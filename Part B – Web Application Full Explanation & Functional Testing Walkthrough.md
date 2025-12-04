# Part B – Web Application: Full Explanation & Functional Testing Walkthrough

## **Task 0 – Application Setup & Database Design**

### **Purpose**

建立后端数据库、配置文件结构，并实现最小权限原则（least privilege）。

**Components**

- `config.py`（读取 .env，配置数据库和上传目录）
- `.env`（数据库账号 + SECRET_KEY）
- `database/schema.sql`（建表脚本）
- `database/db.py`（get_db / CRUD 操作）

### **Key Implementations**

**Database schema**

三张表：

1. `users`
   - email UNIQUE
   - password_hash（PBKDF2哈希）
   - role (‘user’ or ‘admin’)
   - failed_logins、locked_until（防暴力破解）
   - created_at
2. `evaluation_requests`
   - 外键 user_id
   - comment / preferred_contact
   - image_filename
3. `password_resets`
   - token（高熵31~43字节）
   - expires_at
   - used

**Security Design**

- 使用 **专用 MySQL 用户 lovejoy_user**（不得使用 root）
- 数据库访问全部使用 **参数化 SQL**



## **Task 1 – User Registration System**

### **Purpose**

允许新用户创建账户并安全存储密码。

### **Components**

- `templates/register.html`
- `app.py` → `/register` route
- `utils/security.py` → 密码强度 + PBKDF2
- `database/db.py` → create_user

### **Key Implementations**

Strong password policy

你实现了：

- ≥ 8 characters
- Uppercase
- Lowercase
- Number
- Special character

### Secure password storage

使用：

```
generate_password_hash(password)
```

→ PBKDF2 + 盐（werkzeug 内置）。

### Input validation

- 邮箱标准化 `.lower()`
- comment、name 清洗 `.strip()`
- 邮箱唯一检查
- CSRF 保护（表单中 hidden token）

------

### **Testing – Task 1**

### **Step 1 – Open registration page**

Visit:

```
/register
```

Form should load.

### **Step 2 – Try weak password**

Expect flash:

> Password must contain …

### **Step 3 – Register valid user**

Input:

- email
- name
- phone
- strong password

Expect:

- success flash
- redirect to `/login`
- database `users` 表新增一条记录
- password_hash 为长哈希，不是明文



## **Task 2 – Login System + Session Management + Account Locking**

### **Purpose**

实现安全登录、会话管理以及防止暴力破解攻击。

### **Components**

- `templates/login.html`
- `app.py` → `/login` & `/logout`
- `utils/auth.py` → login_required, admin_required
- `database/db.py` → increment_failed_login, reset_failed_logins

### **Key Implementations**

Password verification

```
check_password_hash(stored_hash, password_input)
```

Account lockout system

你实现了：

- 连续 5 次失败 → 锁定账户
- 锁定时间 15 分钟
- locked_until 自动递减
- 登录成功 → 重置计数

Session storage

存储：

```
session['user_id']
session['email']
session['role']
```

### CSRF protection

每个 POST 请求都验证 token。

------

### **Testing – Task 2**

### **Case 1: Normal login**

使用 Task1 注册的用户登录
 Expect:

- redirect to index
- navbar 显示 "Hello, email" 和 Logout

### **Case 2: Wrong password × 5**

Expect:

```
Account locked. Try again in X minutes
```

数据库中：

- failed_logins = 5
- locked_until > current time

### **Case 3: Try again during lock period**

同样提示 locked。

### **Case 4: Login after 15+ minutes**

或者手动在 SQL 中修改时间
 Expect：

- 登录成功
- failed_logins = 0
- locked_until = NULL





## **Task 3 – Password Reset System (Token-based)**

### **Purpose**

实现安全的“忘记密码”功能，基于 token、过期时间、单次使用。

### **Components**

- `forgot_password.html`
- `reset_password.html`
- `utils/email_utils.py`（开发模式下打印链接）
- `database/db.py`
- `app.py` → `/forgot-password` & `/reset-password`

### **Key Implementations**

### High-entropy token

```
token_urlsafe(32)
```

### Expiration & single use

表中保存：

- expires_at（1小时）
- used（0 or 1）

### Secure update

重置密码会：

- 检查 token 是否存在
- 检查 expired
- 检查 used
- 检查强密码策略
- 使用 PBKDF2 重设密码

### Cannot enumerate emails

无论邮箱是否存在，提示相同消息：

> If an account with that email exists…

------

### **Testing – Task 3**

### **Case 1: Request reset**

Visit:

```
/forgot-password
```

输入 email
 Expect:

- flash success
- terminal log 打印 reset link
- password_resets 表新增记录

### **Case 2: Click reset link**

Expect reset form load.

### **Case 3: Submit weak password**

Expect flash error.

### **Case 4: Submit valid password**

Expect success.

### **Case 5: Click same link again**

Expect:

```
Invalid or expired password reset link
```





## **Task 4 – Request Evaluation (File Upload + Comment)**

### **Purpose**

允许登录用户提交：

- comment
- contact preference
- image file

并保证上传安全。

### **Components**

- `request_eval.html`
- `upload folder`: `/static/uploads`
- `utils/security.py` → allowed_image_file, generate_safe_filename
- `database/db.py`
- `app.py` → `/request-eval`

### **Key Implementations**

File type whitelist

Only:

```
.jpg, .jpeg, .png, .gif
```

### Random filename generation

```
safe_name = secrets.token_hex(16) + ext
```

避免：

- 原始文件名泄露隐私
- 覆盖同名文件
- 路径遍历

### Upload size restriction

```
MAX_CONTENT_LENGTH = 2MB
```

### XSS protection

- comment 使用模板 autoescape
- image 仅作为静态 file served，不进行解析

### Form CSRF protection

------

### **Testing – Task 4**

### **Case 1: Upload valid JPG**

Expect:

- success flash
- record appears in list
- small thumbnail shown

### **Case 2: Upload .exe/.txt**

Expect:

```
Invalid file type
```

### **Case 3: Large (>2MB) file**

Expect:

```
Request Entity Too Large
```

### **Case 4: Access without login**

Expect redirect to login.



## **Task 5 – Admin Panel (RBAC)**

### **Purpose**

管理员查看所有用户提交的评价请求。

### **Components**

- `admin_list.html`（你的 admin_requests.html）
- `database/db.py` → get_all_evaluation_requests_with_user
- `utils/auth.py` → admin_required
- `app.py` → `/admin/requests`

### **Key Implementations**

### Role-Based Access Control

用户 row 中：

```
role = "admin"
```

路由保护：

```
@admin_required
def admin_requests():
```

只有 admin 可访问。

### Full joined table view

管理员可见：

- user name/email/phone
- comment
- contact preference
- timestamp
- image preview

### Security

- 普通用户访问 → “Admin access only.”
- 未登录用户访问 → redirect login
- 所有字段都有自动 HTML 转义（防 stored XSS）

------

### **Testing – Task 5**

### **Case 1: Normal user**

访问：

```
/admin/requests
```

Expect:

- redirect index
- flash “Admin access only.”

### **Case 2: Admin**

Expect管理员界面加载，表格显示所有请求。

### **Case 3: Admin logged out**

访问 → redirect login。