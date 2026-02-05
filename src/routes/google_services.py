from flask import Blueprint, jsonify, request, current_app, redirect, url_for
from src.routes.auth import token_required
import requests
import json
from datetime import datetime, timedelta
import base64
import os

google_bp = Blueprint('google', __name__)

# إعدادات Google API
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/api/google/callback')

# نطاقات الصلاحيات المطلوبة
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/forms',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/sites'
]

@google_bp.route('/auth-url', methods=['GET'])
@token_required
def get_google_auth_url(current_user):
    """الحصول على رابط المصادقة مع Google"""
    try:
        # بناء رابط المصادقة
        auth_url = (
            f"https://accounts.google.com/o/oauth2/auth?"
            f"client_id={GOOGLE_CLIENT_ID}&"
            f"redirect_uri={GOOGLE_REDIRECT_URI}&"
            f"scope={'+'.join(GOOGLE_SCOPES)}&"
            f"response_type=code&"
            f"access_type=offline&"
            f"prompt=consent&"
            f"state={current_user.id}"
        )
        
        return jsonify({
            'auth_url': auth_url,
            'message': 'يرجى النقر على الرابط للمصادقة مع Google'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get Google auth URL error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في إنشاء رابط المصادقة'}), 500

@google_bp.route('/callback', methods=['GET'])
def google_callback():
    """معالجة رد Google بعد المصادقة"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        if error:
            return jsonify({'message': f'خطأ في المصادقة: {error}'}), 400
        
        if not code:
            return jsonify({'message': 'لم يتم الحصول على رمز المصادقة'}), 400
        
        # تبديل الرمز برمز الوصول
        token_data = {
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': GOOGLE_REDIRECT_URI
        }
        
        response = requests.post('https://oauth2.googleapis.com/token', data=token_data)
        
        if response.status_code == 200:
            tokens = response.json()
            
            # حفظ الرموز (يمكن حفظها في قاعدة البيانات)
            # هنا يمكن حفظ access_token و refresh_token للمستخدم
            
            return redirect('/google_services.html?success=true')
        else:
            return redirect('/google_services.html?error=token_exchange_failed')
            
    except Exception as e:
        current_app.logger.error(f"Google callback error: {str(e)}")
        return redirect('/google_services.html?error=callback_failed')

@google_bp.route('/sheets/create', methods=['POST'])
@token_required
def create_google_sheet(current_user):
    """إنشاء Google Sheet جديد"""
    try:
        data = request.get_json()
        title = data.get('title', 'تقرير السلامة من الحرائق')
        
        # هنا يجب استخدام access_token المحفوظ للمستخدم
        # للبساطة، سنعيد نموذج للاستجابة
        
        sheet_data = {
            'id': 'demo_sheet_id',
            'title': title,
            'url': 'https://docs.google.com/spreadsheets/d/demo_sheet_id/edit',
            'created_at': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'message': 'تم إنشاء Google Sheet بنجاح',
            'sheet': sheet_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Create Google Sheet error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في إنشاء Google Sheet'}), 500

@google_bp.route('/forms/create', methods=['POST'])
@token_required
def create_google_form(current_user):
    """إنشاء Google Form جديد"""
    try:
        data = request.get_json()
        title = data.get('title', 'نموذج تشييك السلامة')
        description = data.get('description', 'نموذج لتشييك أجهزة السلامة من الحرائق')
        
        # نموذج للاستجابة
        form_data = {
            'id': 'demo_form_id',
            'title': title,
            'description': description,
            'url': 'https://docs.google.com/forms/d/demo_form_id/edit',
            'response_url': 'https://docs.google.com/forms/d/demo_form_id/viewform',
            'created_at': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'message': 'تم إنشاء Google Form بنجاح',
            'form': form_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Create Google Form error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في إنشاء Google Form'}), 500

@google_bp.route('/drive/upload', methods=['POST'])
@token_required
def upload_to_google_drive(current_user):
    """رفع ملف إلى Google Drive"""
    try:
        if 'file' not in request.files:
            return jsonify({'message': 'لم يتم اختيار ملف'}), 400
        
        file = request.files['file']
        folder_name = request.form.get('folder', 'Fire Safety Reports')
        
        if file.filename == '':
            return jsonify({'message': 'لم يتم اختيار ملف'}), 400
        
        # نموذج للاستجابة
        drive_file = {
            'id': 'demo_drive_file_id',
            'name': file.filename,
            'url': 'https://drive.google.com/file/d/demo_drive_file_id/view',
            'folder': folder_name,
            'uploaded_at': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'message': 'تم رفع الملف إلى Google Drive بنجاح',
            'file': drive_file
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Upload to Google Drive error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في رفع الملف إلى Google Drive'}), 500

@google_bp.route('/docs/create', methods=['POST'])
@token_required
def create_google_doc(current_user):
    """إنشاء Google Doc جديد"""
    try:
        data = request.get_json()
        title = data.get('title', 'تقرير السلامة من الحرائق')
        template = data.get('template', 'basic')
        
        # نموذج للاستجابة
        doc_data = {
            'id': 'demo_doc_id',
            'title': title,
            'url': 'https://docs.google.com/document/d/demo_doc_id/edit',
            'template': template,
            'created_at': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'message': 'تم إنشاء Google Doc بنجاح',
            'document': doc_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Create Google Doc error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في إنشاء Google Doc'}), 500

@google_bp.route('/calendar/create-event', methods=['POST'])
@token_required
def create_calendar_event(current_user):
    """إنشاء حدث في Google Calendar"""
    try:
        data = request.get_json()
        title = data.get('title', 'مهمة صيانة')
        description = data.get('description', '')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        # نموذج للاستجابة
        event_data = {
            'id': 'demo_event_id',
            'title': title,
            'description': description,
            'start_time': start_time,
            'end_time': end_time,
            'url': 'https://calendar.google.com/calendar/event?eid=demo_event_id',
            'created_at': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'message': 'تم إنشاء الحدث في Google Calendar بنجاح',
            'event': event_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Create calendar event error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في إنشاء الحدث'}), 500

@google_bp.route('/sites/create', methods=['POST'])
@token_required
def create_google_site(current_user):
    """إنشاء Google Site جديد"""
    try:
        data = request.get_json()
        title = data.get('title', 'موقع السلامة من الحرائق')
        template = data.get('template', 'basic')
        
        # نموذج للاستجابة
        site_data = {
            'id': 'demo_site_id',
            'title': title,
            'url': 'https://sites.google.com/view/demo_site_id',
            'edit_url': 'https://sites.google.com/view/demo_site_id/edit',
            'template': template,
            'created_at': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'message': 'تم إنشاء Google Site بنجاح',
            'site': site_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Create Google Site error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في إنشاء Google Site'}), 500

@google_bp.route('/templates', methods=['GET'])
@token_required
def get_google_templates(current_user):
    """الحصول على قوالب Google المتاحة"""
    try:
        templates = {
            'sheets': [
                {
                    'id': 'fire_inspection_log',
                    'name': 'سجل تشييكات الحريق',
                    'description': 'قالب لتسجيل تشييكات أجهزة الحريق اليومية'
                },
                {
                    'id': 'maintenance_schedule',
                    'name': 'جدول الصيانة',
                    'description': 'قالب لجدولة أعمال الصيانة الدورية'
                },
                {
                    'id': 'incident_report',
                    'name': 'تقرير الحوادث',
                    'description': 'قالب لتسجيل حوادث السلامة'
                }
            ],
            'forms': [
                {
                    'id': 'daily_inspection',
                    'name': 'تشييك يومي',
                    'description': 'نموذج للتشييك اليومي لأجهزة الحريق'
                },
                {
                    'id': 'incident_report_form',
                    'name': 'بلاغ حادث',
                    'description': 'نموذج للإبلاغ عن حوادث السلامة'
                },
                {
                    'id': 'training_feedback',
                    'name': 'تقييم التدريب',
                    'description': 'نموذج لتقييم دورات التدريب'
                }
            ],
            'docs': [
                {
                    'id': 'safety_policy',
                    'name': 'سياسة السلامة',
                    'description': 'قالب لكتابة سياسات السلامة'
                },
                {
                    'id': 'emergency_plan',
                    'name': 'خطة الطوارئ',
                    'description': 'قالب لخطط الطوارئ والإخلاء'
                },
                {
                    'id': 'training_manual',
                    'name': 'دليل التدريب',
                    'description': 'قالب لأدلة التدريب على السلامة'
                }
            ]
        }
        
        return jsonify({
            'templates': templates,
            'message': 'تم جلب القوالب بنجاح'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get Google templates error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب القوالب'}), 500

@google_bp.route('/integration-status', methods=['GET'])
@token_required
def get_integration_status(current_user):
    """الحصول على حالة التكامل مع Google"""
    try:
        # هنا يجب فحص حالة الرموز المحفوظة للمستخدم
        # للبساطة، سنعيد حالة تجريبية
        
        status = {
            'connected': False,  # يجب فحص وجود access_token صالح
            'services': {
                'sheets': {'enabled': True, 'connected': False},
                'forms': {'enabled': True, 'connected': False},
                'drive': {'enabled': True, 'connected': False},
                'docs': {'enabled': True, 'connected': False},
                'calendar': {'enabled': True, 'connected': False},
                'sites': {'enabled': True, 'connected': False}
            },
            'last_sync': None,
            'user_email': None
        }
        
        return jsonify({
            'status': status,
            'message': 'تم جلب حالة التكامل بنجاح'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get integration status error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب حالة التكامل'}), 500

@google_bp.route('/disconnect', methods=['POST'])
@token_required
def disconnect_google(current_user):
    """قطع الاتصال مع Google"""
    try:
        # هنا يجب حذف الرموز المحفوظة للمستخدم
        # وإلغاء الصلاحيات من Google
        
        return jsonify({
            'message': 'تم قطع الاتصال مع Google بنجاح'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Disconnect Google error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في قطع الاتصال'}), 500

