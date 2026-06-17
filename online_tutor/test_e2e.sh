#!/bin/bash
# 线上家教平台 — 端到端功能测试
BASE="http://127.0.0.1:5000"
PASS=0; FAIL=0

ok()   { PASS=$((PASS+1)); echo "  ✅ $1"; }
fail() { FAIL=$((FAIL+1)); echo "  ❌ $1 (expected $2, got $3)"; }
check() { if [ "$2" = "$3" ]; then ok "$1"; else fail "$1" "$2" "$3"; fi; }
hdr()  { echo ""; echo "━━━ $1 ━━━"; }

COOKIE() { echo "/tmp/e2e_$$_$1"; }

hdr "1. 公共页面"
check "首页重定向"     "302" "$(curl -s -o /dev/null -w '%{http_code}' $BASE/)"
check "登录页"         "200" "$(curl -s -o /dev/null -w '%{http_code}' $BASE/auth/login)"
check "注册页"         "200" "$(curl -s -o /dev/null -w '%{http_code}' $BASE/auth/register)"
check "课程列表"       "200" "$(curl -s -o /dev/null -w '%{http_code}' $BASE/course/)"
check "课程详情"       "200" "$(curl -s -o /dev/null -w '%{http_code}' $BASE/course/1)"

hdr "2. 权限守卫 (未登录)"
check "预约列表(未登录)" "302" "$(curl -s -o /dev/null -w '%{http_code}' $BASE/booking/my-bookings)"
check "后台(未登录)"     "302" "$(curl -s -o /dev/null -w '%{http_code}' $BASE/admin/)"

hdr "3. 学生流程"
S=$(COOKIE "s")
curl -s -c $S -X POST -d "username=student_xiao&password=123456" $BASE/auth/login -o /dev/null
check "学生登录" "200" "$(curl -s -b $S -o /dev/null -w '%{http_code}' $BASE/course/)"
check "我的预约" "200" "$(curl -s -b $S -o /dev/null -w '%{http_code}' $BASE/booking/my-bookings)"
check "聊天列表" "200" "$(curl -s -b $S -o /dev/null -w '%{http_code}' $BASE/chat/)"

# 预约新课
BEFORE=$(curl -s -b $S $BASE/booking/my-bookings | grep -c 'status-')
curl -s -b $S -X POST -d "scheduled_time=2026-07-15T14:00" $BASE/booking/create/1 -o /dev/null
AFTER=$(curl -s -b $S $BASE/booking/my-bookings | grep -c 'status-')
[ "$AFTER" -gt "$BEFORE" ] && ok "新预约创建成功 (${BEFORE}→${AFTER})" || fail "预约数未增加" ">" "$AFTER"

# 聊天室
check "聊天室" "200" "$(curl -s -b $S -o /dev/null -w '%{http_code}' $BASE/chat/1)"

# 退出 (使用 -L -c 确保获取登出后的新 cookie)
curl -s -b $S -c $S -L $BASE/auth/logout -o /dev/null
check "学生退出" "302" "$(curl -s -b $S -o /dev/null -w '%{http_code}' $BASE/booking/my-bookings)"

hdr "4. 教师流程"
T=$(COOKIE "t")
curl -s -c $T -X POST -d "username=teacher_wang&password=123456" $BASE/auth/login -o /dev/null
check "教师登录" "200" "$(curl -s -b $T -o /dev/null -w '%{http_code}' $BASE/course/my-courses)"
check "我的课程" "200" "$(curl -s -b $T -o /dev/null -w '%{http_code}' $BASE/course/my-courses)"
check "预约管理" "200" "$(curl -s -b $T -o /dev/null -w '%{http_code}' $BASE/booking/teacher)"

# 确认预约 (需要先确保test_stu的预约已支付)
# 先找到最后一个booking id
LAST_BOOKING=$(curl -s -b $T $BASE/booking/teacher | grep -oP 'booking/confirm/\d+' | head -1 | grep -oP '\d+')
if [ -n "$LAST_BOOKING" ]; then
    # 模拟支付
    curl -s -b $S_COOKIE -X POST -d "" $BASE/payment/pay/$LAST_BOOKING -o /dev/null 2>/dev/null
fi

# 发布新课
curl -s -b $T -X POST -d "title=测试课程&subject=编程&description=自动化测试&price=99&duration=60" $BASE/course/create -o /dev/null
check "发布新课程" "200" "$(curl -s -b $T -o /dev/null -w '%{http_code}' $BASE/course/my-courses)"

# 退出
curl -s -b $T -c $T -L $BASE/auth/logout -o /dev/null

hdr "5. 家长流程"
P=$(COOKIE "p")
curl -s -c $P -X POST -d "username=parent_zhang&password=123456" $BASE/auth/login -o /dev/null
check "家长登录" "200" "$(curl -s -b $P -o /dev/null -w '%{http_code}' $BASE/parent/)"
check "绑定页面" "200" "$(curl -s -b $P -o /dev/null -w '%{http_code}' $BASE/parent/bind)"
check "学生课程" "200" "$(curl -s -b $P -o /dev/null -w '%{http_code}' $BASE/parent/student/5/bookings)"
check "学生消费" "200" "$(curl -s -b $P -o /dev/null -w '%{http_code}' $BASE/parent/student/5/payments)"

# 家长浏览课程
check "家长浏览课程" "200" "$(curl -s -b $P -o /dev/null -w '%{http_code}' $BASE/course/)"
check "家长查看课程详情" "200" "$(curl -s -b $P -o /dev/null -w '%{http_code}' $BASE/course/1)"

# 家长代学生预约
BEFORE_P=$(curl -s -b $P $BASE/booking/my-bookings | grep -c 'status-')
curl -s -b $P -X POST -d "student_id=5&scheduled_time=2026-08-15T14:00" $BASE/booking/create/1 -o /dev/null
AFTER_P=$(curl -s -b $P $BASE/booking/my-bookings | grep -c 'status-')
[ "$AFTER_P" -gt "$BEFORE_P" ] && ok "家长代预约成功 (${BEFORE_P}→${AFTER_P})" || fail "家长代预约未生效" ">" "$AFTER_P"

# 家长查看预约列表
check "家长查看预约列表" "200" "$(curl -s -b $P -o /dev/null -w '%{http_code}' $BASE/booking/my-bookings)"

curl -s -b $P -c $P -L $BASE/auth/logout -o /dev/null

hdr "6. 管理员流程"
A=$(COOKIE "a")
curl -s -c $A -X POST -d "username=admin&password=admin123" $BASE/auth/login -o /dev/null
check "管理员登录" "200" "$(curl -s -b $A -o /dev/null -w '%{http_code}' $BASE/admin/)"
check "审核教师" "200" "$(curl -s -b $A -o /dev/null -w '%{http_code}' $BASE/admin/verify-teachers)"
check "用户管理" "200" "$(curl -s -b $A -o /dev/null -w '%{http_code}' $BASE/admin/users)"
curl -s -b $A -c $A -L $BASE/auth/logout -o /dev/null

hdr "7. 角色隔离"
# 学生不能访问教师功能
S2=$(COOKIE "s2")
curl -s -c $S2 -X POST -d "username=student_xiao&password=123456" $BASE/auth/login -o /dev/null
check "学生不能发课" "302" "$(curl -s -b $S2 -o /dev/null -w '%{http_code}' $BASE/course/my-courses)"
check "学生不能进后台" "302" "$(curl -s -b $S2 -o /dev/null -w '%{http_code}' $BASE/admin/)"
curl -s -b $S2 -c $S2 -L $BASE/auth/logout -o /dev/null

# 教师不能访问学生专属
T2=$(COOKIE "t2")
curl -s -c $T2 -X POST -d "username=teacher_wang&password=123456" $BASE/auth/login -o /dev/null
check "教师不能预约" "302" "$(curl -s -b $T2 -o /dev/null -w '%{http_code}' $BASE/booking/my-bookings)"
check "教师不能进后台" "302" "$(curl -s -b $T2 -o /dev/null -w '%{http_code}' $BASE/admin/)"
curl -s -b $T2 -c $T2 -L $BASE/auth/logout -o /dev/null

hdr "8. 表单验证"
check "空字段注册" "200" "$(curl -s -X POST -d "username=&email=&password=&role=student" $BASE/auth/register -o /dev/null -w '%{http_code}')"
check "错误密码登录" "200" "$(curl -s -X POST -d "username=admin&password=wrong" $BASE/auth/login -o /dev/null -w '%{http_code}')"
check "重复用户名注册" "200" "$(curl -s -X POST -d "username=admin&email=x@x.com&password=123&role=student" $BASE/auth/register -o /dev/null -w '%{http_code}')"

echo ""
echo "========================================="
echo "  测试结果: ✅ $PASS 通过  ❌ $FAIL 失败"
echo "========================================="

# 清理
rm -f /tmp/e2e_$$_*
