from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import jwt
import os

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')
    department = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(255))
    reset_token = db.Column(db.String(255))
    reset_token_expires = db.Column(db.DateTime)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # علاقات مع الجداول الأخرى
    inspections = db.relationship('Inspection', backref='inspector', lazy=True)
    maintenance_tasks = db.relationship('MaintenanceTask', backref='assigned_user', lazy=True)
    uploaded_files = db.relationship('UploadedFile', backref='uploader', lazy=True)

    def __repr__(self):
        return f'<User {self.email}>'

    def set_password(self, password):
        """تعيين كلمة مرور مشفرة"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """التحقق من كلمة المرور"""
        return check_password_hash(self.password_hash, password)

    def generate_token(self, expires_in=3600):
        """إنشاء رمز JWT للمصادقة"""
        payload = {
            'user_id': self.id,
            'email': self.email,
            'exp': datetime.utcnow().timestamp() + expires_in
        }
        return jwt.encode(payload, os.environ.get('SECRET_KEY', 'default-secret'), algorithm='HS256')

    @staticmethod
    def verify_token(token):
        """التحقق من صحة الرمز المميز"""
        try:
            payload = jwt.decode(token, os.environ.get('SECRET_KEY', 'default-secret'), algorithms=['HS256'])
            return User.query.get(payload['user_id'])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def generate_verification_token(self):
        """إنشاء رمز التحقق من البريد الإلكتروني"""
        payload = {
            'user_id': self.id,
            'email': self.email,
            'action': 'verify_email',
            'exp': datetime.utcnow().timestamp() + 86400  # 24 ساعة
        }
        return jwt.encode(payload, os.environ.get('SECRET_KEY', 'default-secret'), algorithm='HS256')

    def generate_reset_token(self):
        """إنشاء رمز إعادة تعيين كلمة المرور"""
        payload = {
            'user_id': self.id,
            'email': self.email,
            'action': 'reset_password',
            'exp': datetime.utcnow().timestamp() + 3600  # ساعة واحدة
        }
        return jwt.encode(payload, os.environ.get('SECRET_KEY', 'default-secret'), algorithm='HS256')

    @staticmethod
    def verify_reset_token(token):
        """التحقق من رمز إعادة تعيين كلمة المرور"""
        try:
            payload = jwt.decode(token, os.environ.get('SECRET_KEY', 'default-secret'), algorithms=['HS256'])
            if payload.get('action') == 'reset_password':
                return User.query.get(payload['user_id'])
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            pass
        return None

    def update_last_login(self):
        """تحديث وقت آخر تسجيل دخول"""
        self.last_login = datetime.utcnow()
        db.session.commit()

    def is_admin(self):
        """التحقق من كون المستخدم مدير"""
        return self.role in ['admin', 'super_admin']

    def is_safety_manager(self):
        """التحقق من كون المستخدم مسؤول سلامة"""
        return self.role in ['safety_manager', 'admin', 'super_admin']

    def can_manage_users(self):
        """التحقق من صلاحية إدارة المستخدمين"""
        return self.role in ['admin', 'super_admin']

    def to_dict(self, include_sensitive=False):
        """تحويل المستخدم إلى قاموس"""
        data = {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'department': self.department,
            'phone': self.phone,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_sensitive:
            data.update({
                'verification_token': self.verification_token,
                'reset_token': self.reset_token,
                'reset_token_expires': self.reset_token_expires.isoformat() if self.reset_token_expires else None
            })
        
        return data

    @staticmethod
    def create_admin_user():
        """إنشاء المستخدم المدير الافتراضي"""
        admin_email = 'alisallwe22@gmail.com'
        existing_admin = User.query.filter_by(email=admin_email).first()
        
        if not existing_admin:
            admin = User(
                email=admin_email,
                name='علي صلوي',
                role='super_admin',
                department='إدارة السلامة',
                is_active=True,
                is_verified=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            return admin
        return existing_admin


class UserSession(db.Model):
    """جدول جلسات المستخدمين للتذكر"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_token = db.Column(db.String(255), unique=True, nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='sessions')

    def is_expired(self):
        """التحقق من انتهاء صلاحية الجلسة"""
        return datetime.utcnow() > self.expires_at

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_token': self.session_token,
            'ip_address': self.ip_address,
            'expires_at': self.expires_at.isoformat(),
            'created_at': self.created_at.isoformat()
        }


class UserProfile(db.Model):
    """ملف المستخدم الشخصي المفصل"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    avatar_url = db.Column(db.String(255))
    bio = db.Column(db.Text)
    address = db.Column(db.Text)
    emergency_contact = db.Column(db.String(100))
    emergency_phone = db.Column(db.String(20))
    certifications = db.Column(db.Text)  # JSON string
    training_records = db.Column(db.Text)  # JSON string
    preferences = db.Column(db.Text)  # JSON string للإعدادات الشخصية
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('profile', uselist=False))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'avatar_url': self.avatar_url,
            'bio': self.bio,
            'address': self.address,
            'emergency_contact': self.emergency_contact,
            'emergency_phone': self.emergency_phone,
            'certifications': self.certifications,
            'training_records': self.training_records,
            'preferences': self.preferences,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


# نماذج إضافية للنظام
class Inspection(db.Model):
    """جدول التشييكات"""
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    inspector_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    inspection_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False)  # good, warning, danger
    notes = db.Column(db.Text)
    images = db.Column(db.Text)  # JSON string للصور
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Device(db.Model):
    """جدول الأجهزة"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    serial_number = db.Column(db.String(100))
    installation_date = db.Column(db.Date)
    last_maintenance = db.Column(db.Date)
    next_maintenance = db.Column(db.Date)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    inspections = db.relationship('Inspection', backref='device', lazy=True)
    maintenance_tasks = db.relationship('MaintenanceTask', backref='device', lazy=True)


class MaintenanceTask(db.Model):
    """جدول مهام الصيانة"""
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    assigned_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed, cancelled
    scheduled_date = db.Column(db.DateTime)
    completed_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UploadedFile(db.Model):
    """جدول الملفات المرفوعة"""
    id = db.Column(db.Integer, primary_key=True)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(50))  # forms, reports, images, etc.
    description = db.Column(db.Text)
    is_public = db.Column(db.Boolean, default=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)


class SystemSettings(db.Model):
    """إعدادات النظام"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def get_setting(key, default=None):
        """الحصول على إعداد معين"""
        setting = SystemSettings.query.filter_by(key=key).first()
        return setting.value if setting else default

    @staticmethod
    def set_setting(key, value, description=None):
        """تعيين إعداد معين"""
        setting = SystemSettings.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            setting.updated_at = datetime.utcnow()
            if description:
                setting.description = description
        else:
            setting = SystemSettings(key=key, value=value, description=description)
            db.session.add(setting)
        db.session.commit()
        return setting


class AutoSaveData(db.Model):
    """بيانات الحفظ التلقائي"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    page_path = db.Column(db.String(255), nullable=False)
    data = db.Column(db.Text, nullable=False)  # JSON string
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='auto_save_data')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'page_path': self.page_path,
            'data': self.data,
            'timestamp': self.timestamp.isoformat()
        }

