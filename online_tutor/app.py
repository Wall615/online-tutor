import os
import secrets
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, session, abort
from flask_login import LoginManager
from config import Config
from models import db, User

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录后再访问此页面。'


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    # ---- Logging ----
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=1024 * 1024,
        backupCount=5
    )
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s [%(name)s] %(message)s'
    ))
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Application starting')

    # Register blueprints
    from auth.routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from course.routes import course_bp
    app.register_blueprint(course_bp, url_prefix='/course')

    from booking.routes import booking_bp
    app.register_blueprint(booking_bp, url_prefix='/booking')

    from chat.routes import chat_bp
    app.register_blueprint(chat_bp, url_prefix='/chat')

    from review.routes import review_bp
    app.register_blueprint(review_bp, url_prefix='/review')

    from parent.routes import parent_bp
    app.register_blueprint(parent_bp, url_prefix='/parent')

    from payment.routes import payment_bp
    app.register_blueprint(payment_bp, url_prefix='/payment')

    from admin.routes import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # ---- CSRF Protection ----
    def generate_csrf_token():
        if '_csrf_token' not in session:
            session['_csrf_token'] = secrets.token_hex(32)
        return session['_csrf_token']

    @app.before_request
    def csrf_protect():
        if request.method != 'POST':
            return
        # Skip CSRF in DEBUG mode (E2E tests)
        if app.config.get('DEBUG'):
            return
        token = session.get('_csrf_token')
        if not token:
            app.logger.error('CSRF: token missing from session')
            abort(400)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            submitted = request.headers.get('X-CSRF-Token', '')
        else:
            submitted = request.form.get('_csrf_token', '')
        if not secrets.compare_digest(token, submitted):
            app.logger.warning(f'CSRF validation failed for {request.path}')
            abort(400)

    # ---- Context processors ----
    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        from models import Message

        result = {'csrf_token': generate_csrf_token()}

        if current_user.is_authenticated:
            result['unread_count'] = Message.query.filter_by(
                receiver_id=current_user.id, is_read=False
            ).count()
        else:
            result['unread_count'] = 0

        return result
        from flask_login import current_user
        from models import Message
        if current_user.is_authenticated:
            count = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
            return {'unread_count': count}
        return {'unread_count': 0}

    # Home route
    @app.route('/')
    def index():
        from flask import redirect
        return redirect('/course/')

    # ---- Error Handlers ----
    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        app.logger.error(f'500 Internal Server Error: {e}')
        return render_template('500.html'), 500

    with app.app_context():
        db.create_all()

    return app


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0')
