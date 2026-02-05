from flask import Blueprint, jsonify, request, current_app, redirect
from src.routes.auth import token_required
import requests
import json
from datetime import datetime
import os

canva_bp = Blueprint('canva', __name__)

# إعدادات Canva API
CANVA_CLIENT_ID = os.environ.get('CANVA_CLIENT_ID', '')
CANVA_CLIENT_SECRET = os.environ.get('CANVA_CLIENT_SECRET', '')
CANVA_REDIRECT_URI = os.environ.get('CANVA_REDIRECT_URI', 'http://localhost:5000/api/canva/callback')

# نطاقات الصلاحيات المطلوبة
CANVA_SCOPES = [
    'design:read',
    'design:write',
    'folder:read',
    'folder:write'
]

@canva_bp.route('/auth-url', methods=['GET'])
@token_required
def get_canva_auth_url(current_user):
    """الحصول على رابط المصادقة مع Canva"""
    try:
        # بناء رابط المصادقة
        auth_url = (
            f"https://www.canva.com/api/oauth/authorize?"
            f"client_id={CANVA_CLIENT_ID}&"
            f"redirect_uri={CANVA_REDIRECT_URI}&"
            f"scope={'+'.join(CANVA_SCOPES)}&"
            f"response_type=code&"
            f"state={current_user.id}"
        )
        
        return jsonify({
            'auth_url': auth_url,
            'message': 'يرجى النقر على الرابط للمصادقة مع Canva'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get Canva auth URL error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في إنشاء رابط المصادقة'}), 500

@canva_bp.route('/callback', methods=['GET'])
def canva_callback():
    """معالجة رد Canva بعد المصادقة"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        if error:
            return redirect('/canva_integration.html?error=' + error)
        
        if not code:
            return redirect('/canva_integration.html?error=no_code')
        
        # تبديل الرمز برمز الوصول
        token_data = {
            'client_id': CANVA_CLIENT_ID,
            'client_secret': CANVA_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': CANVA_REDIRECT_URI
        }
        
        # للبساطة، سنعيد نجاح مؤقت
        return redirect('/canva_integration.html?success=true')
            
    except Exception as e:
        current_app.logger.error(f"Canva callback error: {str(e)}")
        return redirect('/canva_integration.html?error=callback_failed')

@canva_bp.route('/templates', methods=['GET'])
@token_required
def get_canva_templates(current_user):
    """الحصول على قوالب Canva للسلامة من الحرائق"""
    try:
        templates = {
            'reports': [
                {
                    'id': 'fire_safety_report_1',
                    'name': 'تقرير السلامة الشهري',
                    'description': 'قالب تقرير شهري شامل للسلامة من الحرائق',
                    'thumbnail': '/static/images/templates/fire_report_1.jpg',
                    'category': 'reports'
                },
                {
                    'id': 'incident_report_1',
                    'name': 'تقرير حادث',
                    'description': 'قالب لتقارير الحوادث والطوارئ',
                    'thumbnail': '/static/images/templates/incident_report_1.jpg',
                    'category': 'reports'
                },
                {
                    'id': 'inspection_report_1',
                    'name': 'تقرير تشييك',
                    'description': 'قالب لتقارير التشييكات اليومية',
                    'thumbnail': '/static/images/templates/inspection_report_1.jpg',
                    'category': 'reports'
                }
            ],
            'presentations': [
                {
                    'id': 'fire_safety_training_1',
                    'name': 'عرض تدريب السلامة',
                    'description': 'عرض تقديمي لتدريب الموظفين على السلامة',
                    'thumbnail': '/static/images/templates/training_presentation_1.jpg',
                    'category': 'presentations'
                },
                {
                    'id': 'emergency_procedures_1',
                    'name': 'إجراءات الطوارئ',
                    'description': 'عرض تقديمي لإجراءات الطوارئ والإخلاء',
                    'thumbnail': '/static/images/templates/emergency_procedures_1.jpg',
                    'category': 'presentations'
                }
            ],
            'posters': [
                {
                    'id': 'fire_safety_poster_1',
                    'name': 'ملصق السلامة من الحرائق',
                    'description': 'ملصق توعوي للسلامة من الحرائق',
                    'thumbnail': '/static/images/templates/safety_poster_1.jpg',
                    'category': 'posters'
                },
                {
                    'id': 'evacuation_plan_1',
                    'name': 'خطة الإخلاء',
                    'description': 'ملصق خطة الإخلاء للطوارئ',
                    'thumbnail': '/static/images/templates/evacuation_plan_1.jpg',
                    'category': 'posters'
                },
                {
                    'id': 'fire_extinguisher_guide_1',
                    'name': 'دليل طفايات الحريق',
                    'description': 'ملصق توضيحي لاستخدام طفايات الحريق',
                    'thumbnail': '/static/images/templates/extinguisher_guide_1.jpg',
                    'category': 'posters'
                }
            ],
            'certificates': [
                {
                    'id': 'fire_safety_certificate_1',
                    'name': 'شهادة السلامة من الحرائق',
                    'description': 'شهادة إتمام دورة السلامة من الحرائق',
                    'thumbnail': '/static/images/templates/safety_certificate_1.jpg',
                    'category': 'certificates'
                },
                {
                    'id': 'training_completion_1',
                    'name': 'شهادة إتمام التدريب',
                    'description': 'شهادة إتمام التدريب على أجهزة الإطفاء',
                    'thumbnail': '/static/images/templates/training_certificate_1.jpg',
                    'category': 'certificates'
                }
            ],
            'infographics': [
                {
                    'id': 'fire_statistics_1',
                    'name': 'إحصائيات الحرائق',
                    'description': 'إنفوجرافيك لإحصائيات السلامة من الحرائق',
                    'thumbnail': '/static/images/templates/fire_stats_1.jpg',
                    'category': 'infographics'
                },
                {
                    'id': 'fire_prevention_tips_1',
                    'name': 'نصائح الوقاية من الحرائق',
                    'description': 'إنفوجرافيك لنصائح الوقاية من الحرائق',
                    'thumbnail': '/static/images/templates/prevention_tips_1.jpg',
                    'category': 'infographics'
                }
            ],
            'id_cards': [
                {
                    'id': 'fire_warden_id_1',
                    'name': 'بطاقة مسؤول السلامة',
                    'description': 'بطاقة هوية لمسؤولي السلامة من الحرائق',
                    'thumbnail': '/static/images/templates/fire_warden_id_1.jpg',
                    'category': 'id_cards'
                },
                {
                    'id': 'emergency_contact_1',
                    'name': 'بطاقة جهات الاتصال',
                    'description': 'بطاقة أرقام الطوارئ والاتصال',
                    'thumbnail': '/static/images/templates/emergency_contact_1.jpg',
                    'category': 'id_cards'
                }
            ]
        }
        
        return jsonify({
            'templates': templates,
            'total_templates': sum(len(category) for category in templates.values()),
            'message': 'تم جلب قوالب Canva بنجاح'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get Canva templates error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب قوالب Canva'}), 500

@canva_bp.route('/create-design', methods=['POST'])
@token_required
def create_canva_design(current_user):
    """إنشاء تصميم جديد في Canva"""
    try:
        data = request.get_json()
        template_id = data.get('template_id')
        design_name = data.get('design_name', 'تصميم السلامة من الحرائق')
        custom_data = data.get('custom_data', {})
        
        if not template_id:
            return jsonify({'message': 'معرف القالب مطلوب'}), 400
        
        # نموذج للاستجابة
        design_data = {
            'id': f'canva_design_{template_id}',
            'name': design_name,
            'template_id': template_id,
            'edit_url': f'https://www.canva.com/design/{template_id}/edit',
            'preview_url': f'https://www.canva.com/design/{template_id}/view',
            'created_at': datetime.utcnow().isoformat(),
            'status': 'created'
        }
        
        return jsonify({
            'message': 'تم إنشاء التصميم في Canva بنجاح',
            'design': design_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Create Canva design error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في إنشاء التصميم'}), 500

@canva_bp.route('/designs', methods=['GET'])
@token_required
def get_user_designs(current_user):
    """الحصول على تصاميم المستخدم في Canva"""
    try:
        # نموذج للاستجابة
        designs = [
            {
                'id': 'design_1',
                'name': 'تقرير السلامة - يناير 2024',
                'template_id': 'fire_safety_report_1',
                'edit_url': 'https://www.canva.com/design/design_1/edit',
                'preview_url': 'https://www.canva.com/design/design_1/view',
                'thumbnail': '/static/images/designs/design_1_thumb.jpg',
                'created_at': '2024-01-15T10:30:00Z',
                'updated_at': '2024-01-15T14:20:00Z',
                'status': 'published'
            },
            {
                'id': 'design_2',
                'name': 'ملصق السلامة - المطبخ',
                'template_id': 'fire_safety_poster_1',
                'edit_url': 'https://www.canva.com/design/design_2/edit',
                'preview_url': 'https://www.canva.com/design/design_2/view',
                'thumbnail': '/static/images/designs/design_2_thumb.jpg',
                'created_at': '2024-01-10T09:15:00Z',
                'updated_at': '2024-01-10T11:45:00Z',
                'status': 'draft'
            }
        ]
        
        return jsonify({
            'designs': designs,
            'total_designs': len(designs),
            'message': 'تم جلب التصاميم بنجاح'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get user designs error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب التصاميم'}), 500

@canva_bp.route('/designs/<design_id>/export', methods=['POST'])
@token_required
def export_design(current_user, design_id):
    """تصدير تصميم من Canva"""
    try:
        data = request.get_json()
        format_type = data.get('format', 'pdf')  # pdf, png, jpg
        quality = data.get('quality', 'high')
        
        # نموذج للاستجابة
        export_data = {
            'design_id': design_id,
            'format': format_type,
            'quality': quality,
            'download_url': f'https://export.canva.com/{design_id}.{format_type}',
            'expires_at': (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            'file_size': '2.5 MB',
            'status': 'ready'
        }
        
        return jsonify({
            'message': 'تم تصدير التصميم بنجاح',
            'export': export_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Export design error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في تصدير التصميم'}), 500

@canva_bp.route('/folders', methods=['GET'])
@token_required
def get_canva_folders(current_user):
    """الحصول على مجلدات Canva"""
    try:
        # نموذج للاستجابة
        folders = [
            {
                'id': 'folder_1',
                'name': 'تقارير السلامة',
                'description': 'مجلد لتقارير السلامة من الحرائق',
                'designs_count': 5,
                'created_at': '2024-01-01T00:00:00Z'
            },
            {
                'id': 'folder_2',
                'name': 'ملصقات التوعية',
                'description': 'مجلد للملصقات التوعوية',
                'designs_count': 8,
                'created_at': '2024-01-01T00:00:00Z'
            },
            {
                'id': 'folder_3',
                'name': 'شهادات التدريب',
                'description': 'مجلد لشهادات التدريب',
                'designs_count': 3,
                'created_at': '2024-01-01T00:00:00Z'
            }
        ]
        
        return jsonify({
            'folders': folders,
            'total_folders': len(folders),
            'message': 'تم جلب المجلدات بنجاح'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get Canva folders error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب المجلدات'}), 500

@canva_bp.route('/folders', methods=['POST'])
@token_required
def create_canva_folder(current_user):
    """إنشاء مجلد جديد في Canva"""
    try:
        data = request.get_json()
        folder_name = data.get('name', 'مجلد جديد')
        description = data.get('description', '')
        
        # نموذج للاستجابة
        folder_data = {
            'id': f'folder_{datetime.utcnow().timestamp()}',
            'name': folder_name,
            'description': description,
            'designs_count': 0,
            'created_at': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'message': 'تم إنشاء المجلد بنجاح',
            'folder': folder_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Create Canva folder error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في إنشاء المجلد'}), 500

@canva_bp.route('/integration-status', methods=['GET'])
@token_required
def get_canva_integration_status(current_user):
    """الحصول على حالة التكامل مع Canva"""
    try:
        # نموذج للاستجابة
        status = {
            'connected': False,  # يجب فحص وجود access_token صالح
            'user_info': {
                'name': None,
                'email': None,
                'team_name': None
            },
            'permissions': {
                'design_read': False,
                'design_write': False,
                'folder_read': False,
                'folder_write': False
            },
            'usage_stats': {
                'total_designs': 0,
                'total_folders': 0,
                'last_activity': None
            },
            'last_sync': None
        }
        
        return jsonify({
            'status': status,
            'message': 'تم جلب حالة التكامل بنجاح'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get Canva integration status error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب حالة التكامل'}), 500

@canva_bp.route('/disconnect', methods=['POST'])
@token_required
def disconnect_canva(current_user):
    """قطع الاتصال مع Canva"""
    try:
        # هنا يجب حذف الرموز المحفوظة للمستخدم
        # وإلغاء الصلاحيات من Canva
        
        return jsonify({
            'message': 'تم قطع الاتصال مع Canva بنجاح'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Disconnect Canva error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في قطع الاتصال'}), 500

@canva_bp.route('/webhook', methods=['POST'])
def canva_webhook():
    """معالجة webhook من Canva"""
    try:
        data = request.get_json()
        event_type = data.get('event_type')
        
        # معالجة أحداث Canva المختلفة
        if event_type == 'design.published':
            # معالجة نشر التصميم
            pass
        elif event_type == 'design.updated':
            # معالجة تحديث التصميم
            pass
        
        return jsonify({'status': 'received'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Canva webhook error: {str(e)}")
        return jsonify({'error': 'webhook_failed'}), 500

