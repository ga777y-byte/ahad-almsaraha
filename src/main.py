import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.user import db, User
from src.routes.user import user_bp
from src.routes.auth import auth_bp
from src.routes.users import users_bp
from src.routes.sync import sync_bp
from src.routes.dashboard import dashboard_bp
from src.routes.files import files_bp
from src.routes.google_services import google_bp
from src.routes.canva import canva_bp
from src.routes.inspections import inspections_bp
from src.routes.maintenance import maintenance_bp
from src.routes.devices import devices_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'hospital_fire_safety_secret_key_2024'

# تفعيل CORS للسماح بالطلبات من جميع المصادر
CORS(app, origins="*", allow_headers=["Content-Type", "Authorization"])

# تسجيل المسارات
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(users_bp, url_prefix='/api/users')
app.register_blueprint(sync_bp, url_prefix='/api/sync')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
app.register_blueprint(files_bp, url_prefix='/api/files')
app.register_blueprint(google_bp, url_prefix='/api/google')
app.register_blueprint(canva_bp, url_prefix='/api/canva')
app.register_blueprint(inspections_bp, url_prefix='/api/inspections')
app.register_blueprint(maintenance_bp, url_prefix='/api/maintenance')
app.register_blueprint(devices_bp, url_prefix='/api/devices')

# إعداد قاعدة البيانات
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# إنشاء الجداول والبيانات الأولية
with app.app_context():
    db.create_all()
    
    # إنشاء المستخدم المدير الافتراضي
    admin_user = User.create_admin_user()
    if admin_user:
        print(f"Admin user created/verified: {admin_user.email}")

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404

# معالج الأخطاء
@app.errorhandler(404)
def not_found(error):
    return send_from_directory(app.static_folder, 'index.html')

@app.errorhandler(500)
def internal_error(error):
    return {"error": "Internal server error"}, 500

# إعداد المتغيرات البيئية
os.environ.setdefault('SECRET_KEY', app.config['SECRET_KEY'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

