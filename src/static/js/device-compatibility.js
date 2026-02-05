/**
 * نظام إدارة السلامة من الحرائق - تحسينات التوافق مع الأجهزة
 * يحتوي على تحسينات خاصة لأجهزة iOS, Android, Windows, macOS
 */

class DeviceCompatibility {
    constructor() {
        this.deviceInfo = this.detectDevice();
        this.init();
    }

    /**
     * اكتشاف نوع الجهاز ونظام التشغيل
     */
    detectDevice() {
        const userAgent = navigator.userAgent;
        const platform = navigator.platform;
        
        return {
            // أنظمة التشغيل
            isIOS: /iPad|iPhone|iPod/.test(userAgent) && !window.MSStream,
            isAndroid: /Android/.test(userAgent),
            isWindows: /Win/.test(platform),
            isMacOS: /Mac/.test(platform) && !/iPad|iPhone|iPod/.test(userAgent),
            isLinux: /Linux/.test(platform),
            
            // المتصفحات
            isSafari: /Safari/.test(userAgent) && !/Chrome/.test(userAgent),
            isChrome: /Chrome/.test(userAgent),
            isFirefox: /Firefox/.test(userAgent),
            isEdge: /Edge/.test(userAgent),
            
            // نوع الجهاز
            isMobile: /Mobi|Android/i.test(userAgent),
            isTablet: /iPad|Android(?!.*Mobile)/i.test(userAgent),
            isDesktop: !/Mobi|Android|iPad/i.test(userAgent),
            
            // إمكانيات الجهاز
            hasTouch: 'ontouchstart' in window || navigator.maxTouchPoints > 0,
            hasCamera: 'mediaDevices' in navigator && 'getUserMedia' in navigator.mediaDevices,
            hasGeolocation: 'geolocation' in navigator,
            hasNotifications: 'Notification' in window,
            hasServiceWorker: 'serviceWorker' in navigator,
            
            // معلومات الشاشة
            screenWidth: window.screen.width,
            screenHeight: window.screen.height,
            viewportWidth: window.innerWidth,
            viewportHeight: window.innerHeight,
            pixelRatio: window.devicePixelRatio || 1,
            
            // معلومات إضافية
            userAgent: userAgent,
            platform: platform,
            language: navigator.language || navigator.userLanguage,
            cookieEnabled: navigator.cookieEnabled,
            onlineStatus: navigator.onLine
        };
    }

    /**
     * تهيئة التحسينات حسب نوع الجهاز
     */
    init() {
        this.addDeviceClasses();
        this.setupIOSOptimizations();
        this.setupAndroidOptimizations();
        this.setupWindowsOptimizations();
        this.setupMacOSOptimizations();
        this.setupTouchOptimizations();
        this.setupKeyboardOptimizations();
        this.setupViewportOptimizations();
        this.setupPerformanceOptimizations();
        this.setupAccessibilityOptimizations();
        this.monitorConnectivity();
        
        console.log('Device Compatibility initialized:', this.deviceInfo);
    }

    /**
     * إضافة فئات CSS حسب نوع الجهاز
     */
    addDeviceClasses() {
        const body = document.body;
        const classes = [];

        // نظام التشغيل
        if (this.deviceInfo.isIOS) classes.push('ios');
        if (this.deviceInfo.isAndroid) classes.push('android');
        if (this.deviceInfo.isWindows) classes.push('windows');
        if (this.deviceInfo.isMacOS) classes.push('macos');
        if (this.deviceInfo.isLinux) classes.push('linux');

        // المتصفح
        if (this.deviceInfo.isSafari) classes.push('safari');
        if (this.deviceInfo.isChrome) classes.push('chrome');
        if (this.deviceInfo.isFirefox) classes.push('firefox');
        if (this.deviceInfo.isEdge) classes.push('edge');

        // نوع الجهاز
        if (this.deviceInfo.isMobile) classes.push('mobile');
        if (this.deviceInfo.isTablet) classes.push('tablet');
        if (this.deviceInfo.isDesktop) classes.push('desktop');

        // الإمكانيات
        if (this.deviceInfo.hasTouch) classes.push('touch');
        if (this.deviceInfo.hasCamera) classes.push('has-camera');
        if (this.deviceInfo.hasGeolocation) classes.push('has-geolocation');

        body.classList.add(...classes);
    }

    /**
     * تحسينات خاصة بأجهزة iOS
     */
    setupIOSOptimizations() {
        if (!this.deviceInfo.isIOS) return;

        // إصلاح مشكلة الارتفاع في iOS Safari
        const setVH = () => {
            const vh = window.innerHeight * 0.01;
            document.documentElement.style.setProperty('--vh', `${vh}px`);
        };
        
        setVH();
        window.addEventListener('resize', setVH);
        window.addEventListener('orientationchange', () => {
            setTimeout(setVH, 100);
        });

        // منع التكبير عند التركيز على حقول الإدخال
        const inputs = document.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            if (input.type !== 'file') {
                input.style.fontSize = '16px';
            }
        });

        // إصلاح مشكلة التمرير في iOS
        document.body.style.webkitOverflowScrolling = 'touch';

        // تحسين أداء الرسوم المتحركة
        document.body.style.webkitTransform = 'translate3d(0,0,0)';

        // إصلاح مشكلة الكيبورد في iOS
        this.setupIOSKeyboardFix();
    }

    /**
     * إصلاح مشكلة الكيبورد في iOS
     */
    setupIOSKeyboardFix() {
        let initialViewportHeight = window.innerHeight;

        const handleFocus = (e) => {
            if (e.target.matches('input, textarea, select')) {
                setTimeout(() => {
                    if (window.innerHeight < initialViewportHeight * 0.75) {
                        // الكيبورد مفتوح
                        document.body.classList.add('keyboard-open');
                        e.target.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                }, 300);
            }
        };

        const handleBlur = () => {
            setTimeout(() => {
                if (window.innerHeight >= initialViewportHeight * 0.75) {
                    // الكيبورد مغلق
                    document.body.classList.remove('keyboard-open');
                }
            }, 300);
        };

        document.addEventListener('focusin', handleFocus);
        document.addEventListener('focusout', handleBlur);

        // تحديث الارتفاع عند تغيير الاتجاه
        window.addEventListener('orientationchange', () => {
            setTimeout(() => {
                initialViewportHeight = window.innerHeight;
            }, 500);
        });
    }

    /**
     * تحسينات خاصة بأجهزة Android
     */
    setupAndroidOptimizations() {
        if (!this.deviceInfo.isAndroid) return;

        // تحسين أداء التمرير
        document.body.style.overflowScrolling = 'touch';

        // إصلاح مشكلة الكيبورد في Android
        let initialViewportHeight = window.visualViewport ? window.visualViewport.height : window.innerHeight;

        const handleViewportChange = () => {
            const currentHeight = window.visualViewport ? window.visualViewport.height : window.innerHeight;
            
            if (currentHeight < initialViewportHeight * 0.75) {
                document.body.classList.add('keyboard-open');
            } else {
                document.body.classList.remove('keyboard-open');
            }
        };

        if (window.visualViewport) {
            window.visualViewport.addEventListener('resize', handleViewportChange);
        } else {
            window.addEventListener('resize', handleViewportChange);
        }

        // تحسين أداء الرسوم المتحركة
        document.body.style.transform = 'translateZ(0)';

        // تحسين أداء اللمس
        document.body.style.touchAction = 'manipulation';
    }

    /**
     * تحسينات خاصة بأجهزة Windows
     */
    setupWindowsOptimizations() {
        if (!this.deviceInfo.isWindows) return;

        // تحسين دعم التباين العالي
        if (window.matchMedia('(prefers-contrast: high)').matches) {
            document.body.classList.add('high-contrast');
        }

        // تحسين دعم الحركة المخفضة
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            document.body.classList.add('reduced-motion');
        }

        // تحسين دعم الكيبورد
        this.setupWindowsKeyboardNavigation();
    }

    /**
     * تحسين التنقل بالكيبورد في Windows
     */
    setupWindowsKeyboardNavigation() {
        // إضافة دعم Tab للتنقل
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                document.body.classList.add('keyboard-navigation');
            }
        });

        document.addEventListener('mousedown', () => {
            document.body.classList.remove('keyboard-navigation');
        });

        // تحسين مؤشرات التركيز
        const focusableElements = document.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );

        focusableElements.forEach(element => {
            element.addEventListener('focus', () => {
                if (document.body.classList.contains('keyboard-navigation')) {
                    element.classList.add('keyboard-focus');
                }
            });

            element.addEventListener('blur', () => {
                element.classList.remove('keyboard-focus');
            });
        });
    }

    /**
     * تحسينات خاصة بأجهزة macOS
     */
    setupMacOSOptimizations() {
        if (!this.deviceInfo.isMacOS) return;

        // تحسين التمرير الناعم
        document.body.style.scrollBehavior = 'smooth';

        // تحسين دعم الإيماءات
        if (this.deviceInfo.hasTouch) {
            document.body.style.webkitOverflowScrolling = 'touch';
        }

        // تحسين الخطوط
        document.body.style.webkitFontSmoothing = 'antialiased';
        document.body.style.mozOsxFontSmoothing = 'grayscale';
    }

    /**
     * تحسينات اللمس للأجهزة اللمسية
     */
    setupTouchOptimizations() {
        if (!this.deviceInfo.hasTouch) return;

        // تحسين حجم أهداف اللمس
        const touchTargets = document.querySelectorAll('button, a, input, select, textarea');
        touchTargets.forEach(target => {
            const computedStyle = window.getComputedStyle(target);
            const minSize = 44; // الحد الأدنى الموصى به

            if (parseInt(computedStyle.height) < minSize) {
                target.style.minHeight = `${minSize}px`;
            }
            if (parseInt(computedStyle.width) < minSize) {
                target.style.minWidth = `${minSize}px`;
            }
        });

        // تحسين استجابة اللمس
        document.body.style.touchAction = 'manipulation';

        // إضافة دعم الإيماءات
        this.setupGestureSupport();
    }

    /**
     * إضافة دعم الإيماءات
     */
    setupGestureSupport() {
        let startX, startY, startTime;

        document.addEventListener('touchstart', (e) => {
            const touch = e.touches[0];
            startX = touch.clientX;
            startY = touch.clientY;
            startTime = Date.now();
        }, { passive: true });

        document.addEventListener('touchend', (e) => {
            if (!startX || !startY) return;

            const touch = e.changedTouches[0];
            const endX = touch.clientX;
            const endY = touch.clientY;
            const endTime = Date.now();

            const deltaX = endX - startX;
            const deltaY = endY - startY;
            const deltaTime = endTime - startTime;

            // اكتشاف السحب السريع
            if (deltaTime < 300 && Math.abs(deltaX) > 50) {
                const direction = deltaX > 0 ? 'right' : 'left';
                this.handleSwipe(direction, e);
            }

            startX = startY = null;
        }, { passive: true });
    }

    /**
     * معالجة إيماءة السحب
     */
    handleSwipe(direction, event) {
        const swipeEvent = new CustomEvent('swipe', {
            detail: { direction, originalEvent: event }
        });
        event.target.dispatchEvent(swipeEvent);
    }

    /**
     * تحسينات الكيبورد
     */
    setupKeyboardOptimizations() {
        // إضافة اختصارات الكيبورد
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + S للحفظ
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                this.triggerAutoSave();
            }

            // Escape لإغلاق المودال
            if (e.key === 'Escape') {
                this.closeModals();
            }

            // Enter لتأكيد النماذج
            if (e.key === 'Enter' && e.target.matches('input:not([type="textarea"])')) {
                const form = e.target.closest('form');
                if (form) {
                    const submitButton = form.querySelector('button[type="submit"], input[type="submit"]');
                    if (submitButton) {
                        submitButton.click();
                    }
                }
            }
        });

        // تحسين التنقل بـ Tab
        this.setupTabNavigation();
    }

    /**
     * تحسين التنقل بـ Tab
     */
    setupTabNavigation() {
        const focusableSelector = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
        
        document.addEventListener('keydown', (e) => {
            if (e.key !== 'Tab') return;

            const focusableElements = Array.from(document.querySelectorAll(focusableSelector))
                .filter(el => !el.disabled && el.offsetParent !== null);

            const currentIndex = focusableElements.indexOf(document.activeElement);

            if (e.shiftKey) {
                // Shift + Tab للخلف
                const prevIndex = currentIndex <= 0 ? focusableElements.length - 1 : currentIndex - 1;
                focusableElements[prevIndex]?.focus();
            } else {
                // Tab للأمام
                const nextIndex = currentIndex >= focusableElements.length - 1 ? 0 : currentIndex + 1;
                focusableElements[nextIndex]?.focus();
            }

            e.preventDefault();
        });
    }

    /**
     * تحسينات العرض
     */
    setupViewportOptimizations() {
        // تحديث معلومات العرض عند تغيير الحجم
        const updateViewport = () => {
            this.deviceInfo.viewportWidth = window.innerWidth;
            this.deviceInfo.viewportHeight = window.innerHeight;
            
            // إضافة فئات CSS حسب حجم الشاشة
            document.body.classList.remove('viewport-xs', 'viewport-sm', 'viewport-md', 'viewport-lg', 'viewport-xl');
            
            if (this.deviceInfo.viewportWidth < 576) {
                document.body.classList.add('viewport-xs');
            } else if (this.deviceInfo.viewportWidth < 768) {
                document.body.classList.add('viewport-sm');
            } else if (this.deviceInfo.viewportWidth < 992) {
                document.body.classList.add('viewport-md');
            } else if (this.deviceInfo.viewportWidth < 1200) {
                document.body.classList.add('viewport-lg');
            } else {
                document.body.classList.add('viewport-xl');
            }
        };

        updateViewport();
        window.addEventListener('resize', updateViewport);
        window.addEventListener('orientationchange', () => {
            setTimeout(updateViewport, 100);
        });
    }

    /**
     * تحسينات الأداء
     */
    setupPerformanceOptimizations() {
        // تحسين الصور
        this.optimizeImages();

        // تحسين التمرير
        this.optimizeScrolling();

        // تحسين الرسوم المتحركة
        this.optimizeAnimations();

        // تحسين الذاكرة
        this.optimizeMemory();
    }

    /**
     * تحسين الصور
     */
    optimizeImages() {
        const images = document.querySelectorAll('img');
        
        images.forEach(img => {
            // إضافة التحميل الكسول
            if ('loading' in HTMLImageElement.prototype) {
                img.loading = 'lazy';
            }

            // تحسين جودة الصور للشاشات عالية الدقة
            if (this.deviceInfo.pixelRatio > 1) {
                const src = img.src;
                if (src && !src.includes('@2x')) {
                    const highResSrc = src.replace(/\.(jpg|jpeg|png|webp)$/i, '@2x.$1');
                    img.srcset = `${src} 1x, ${highResSrc} 2x`;
                }
            }
        });
    }

    /**
     * تحسين التمرير
     */
    optimizeScrolling() {
        // استخدام passive listeners للتمرير
        const scrollElements = document.querySelectorAll('.scrollable, .modal-body, .table-responsive');
        
        scrollElements.forEach(element => {
            element.addEventListener('scroll', () => {
                // معالجة التمرير
            }, { passive: true });
        });

        // تحسين التمرير الناعم
        if (this.deviceInfo.isDesktop) {
            document.documentElement.style.scrollBehavior = 'smooth';
        }
    }

    /**
     * تحسين الرسوم المتحركة
     */
    optimizeAnimations() {
        // تقليل الرسوم المتحركة للأجهزة الضعيفة
        if (this.deviceInfo.isMobile && this.deviceInfo.pixelRatio < 2) {
            document.body.classList.add('reduced-animations');
        }

        // احترام تفضيلات المستخدم للحركة
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            document.body.classList.add('no-animations');
        }
    }

    /**
     * تحسين الذاكرة
     */
    optimizeMemory() {
        // تنظيف event listeners غير المستخدمة
        window.addEventListener('beforeunload', () => {
            // تنظيف الذاكرة قبل إغلاق الصفحة
            this.cleanup();
        });

        // مراقبة استخدام الذاكرة
        if ('memory' in performance) {
            setInterval(() => {
                const memInfo = performance.memory;
                if (memInfo.usedJSHeapSize > memInfo.jsHeapSizeLimit * 0.9) {
                    console.warn('High memory usage detected');
                    this.triggerGarbageCollection();
                }
            }, 30000);
        }
    }

    /**
     * تحسينات الوصولية
     */
    setupAccessibilityOptimizations() {
        // إضافة دعم قارئ الشاشة
        this.setupScreenReaderSupport();

        // تحسين التباين
        this.setupContrastOptimizations();

        // إضافة دعم التنقل بالكيبورد
        this.setupKeyboardAccessibility();
    }

    /**
     * دعم قارئ الشاشة
     */
    setupScreenReaderSupport() {
        // إضافة aria-labels للعناصر التفاعلية
        const interactiveElements = document.querySelectorAll('button, a, input, select, textarea');
        
        interactiveElements.forEach(element => {
            if (!element.getAttribute('aria-label') && !element.getAttribute('aria-labelledby')) {
                const text = element.textContent || element.value || element.placeholder;
                if (text) {
                    element.setAttribute('aria-label', text.trim());
                }
            }
        });

        // إضافة live regions للتحديثات الديناميكية
        if (!document.querySelector('[aria-live]')) {
            const liveRegion = document.createElement('div');
            liveRegion.setAttribute('aria-live', 'polite');
            liveRegion.setAttribute('aria-atomic', 'true');
            liveRegion.className = 'sr-only';
            liveRegion.id = 'live-region';
            document.body.appendChild(liveRegion);
        }
    }

    /**
     * تحسين التباين
     */
    setupContrastOptimizations() {
        if (window.matchMedia('(prefers-contrast: high)').matches) {
            document.body.classList.add('high-contrast');
        }

        // مراقبة تغييرات تفضيلات التباين
        window.matchMedia('(prefers-contrast: high)').addEventListener('change', (e) => {
            if (e.matches) {
                document.body.classList.add('high-contrast');
            } else {
                document.body.classList.remove('high-contrast');
            }
        });
    }

    /**
     * تحسين الوصولية بالكيبورد
     */
    setupKeyboardAccessibility() {
        // إضافة مؤشرات التركيز المرئية
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                document.body.classList.add('keyboard-navigation');
            }
        });

        document.addEventListener('mousedown', () => {
            document.body.classList.remove('keyboard-navigation');
        });

        // تحسين ترتيب Tab
        this.optimizeTabOrder();
    }

    /**
     * تحسين ترتيب Tab
     */
    optimizeTabOrder() {
        const elements = document.querySelectorAll('[tabindex]');
        elements.forEach(element => {
            const tabIndex = parseInt(element.getAttribute('tabindex'));
            if (tabIndex > 0) {
                console.warn('Positive tabindex detected:', element);
            }
        });
    }

    /**
     * مراقبة الاتصال
     */
    monitorConnectivity() {
        const updateOnlineStatus = () => {
            this.deviceInfo.onlineStatus = navigator.onLine;
            document.body.classList.toggle('offline', !navigator.onLine);
            
            if (navigator.onLine) {
                this.handleOnline();
            } else {
                this.handleOffline();
            }
        };

        window.addEventListener('online', updateOnlineStatus);
        window.addEventListener('offline', updateOnlineStatus);
        updateOnlineStatus();
    }

    /**
     * معالجة حالة الاتصال
     */
    handleOnline() {
        console.log('Device is online');
        // إعادة تزامن البيانات
        if (window.autoSave) {
            window.autoSave.syncPendingData();
        }
    }

    /**
     * معالجة حالة عدم الاتصال
     */
    handleOffline() {
        console.log('Device is offline');
        // إظهار رسالة للمستخدم
        this.showOfflineMessage();
    }

    /**
     * إظهار رسالة عدم الاتصال
     */
    showOfflineMessage() {
        const message = document.createElement('div');
        message.className = 'alert alert-warning offline-message';
        message.textContent = 'لا يوجد اتصال بالإنترنت. سيتم حفظ البيانات محلياً.';
        message.style.position = 'fixed';
        message.style.top = '10px';
        message.style.right = '10px';
        message.style.zIndex = '9999';
        
        document.body.appendChild(message);
        
        setTimeout(() => {
            if (message.parentNode) {
                message.parentNode.removeChild(message);
            }
        }, 5000);
    }

    /**
     * تشغيل الحفظ التلقائي
     */
    triggerAutoSave() {
        if (window.autoSave) {
            window.autoSave.saveAllData();
        }
    }

    /**
     * إغلاق النوافذ المنبثقة
     */
    closeModals() {
        const modals = document.querySelectorAll('.modal.show');
        modals.forEach(modal => {
            const closeButton = modal.querySelector('.btn-close, [data-dismiss="modal"]');
            if (closeButton) {
                closeButton.click();
            }
        });
    }

    /**
     * تشغيل جمع القمامة
     */
    triggerGarbageCollection() {
        // تنظيف المتغيرات غير المستخدمة
        if (window.gc) {
            window.gc();
        }
    }

    /**
     * تنظيف الموارد
     */
    cleanup() {
        // إزالة event listeners
        window.removeEventListener('resize', this.updateViewport);
        window.removeEventListener('orientationchange', this.updateViewport);
        window.removeEventListener('online', this.updateOnlineStatus);
        window.removeEventListener('offline', this.updateOnlineStatus);
    }

    /**
     * الحصول على معلومات الجهاز
     */
    getDeviceInfo() {
        return this.deviceInfo;
    }

    /**
     * فحص دعم ميزة معينة
     */
    supportsFeature(feature) {
        const features = {
            touch: this.deviceInfo.hasTouch,
            camera: this.deviceInfo.hasCamera,
            geolocation: this.deviceInfo.hasGeolocation,
            notifications: this.deviceInfo.hasNotifications,
            serviceWorker: this.deviceInfo.hasServiceWorker,
            webgl: !!window.WebGLRenderingContext,
            webrtc: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia),
            websockets: !!window.WebSocket,
            localStorage: !!window.localStorage,
            sessionStorage: !!window.sessionStorage,
            indexedDB: !!window.indexedDB,
            webWorkers: !!window.Worker,
            fullscreen: !!(document.fullscreenEnabled || document.webkitFullscreenEnabled),
            vibration: !!navigator.vibrate,
            battery: !!navigator.getBattery,
            deviceMotion: !!window.DeviceMotionEvent,
            deviceOrientation: !!window.DeviceOrientationEvent
        };

        return features[feature] || false;
    }

    /**
     * تحسين الأداء حسب نوع الجهاز
     */
    optimizeForDevice() {
        if (this.deviceInfo.isMobile) {
            // تحسينات للأجهزة المحمولة
            document.body.classList.add('mobile-optimized');
            
            // تقليل جودة الصور
            const images = document.querySelectorAll('img');
            images.forEach(img => {
                if (img.src && !img.src.includes('low-quality')) {
                    img.style.imageRendering = 'optimizeSpeed';
                }
            });
            
            // تقليل الرسوم المتحركة
            document.body.classList.add('reduced-animations');
        }

        if (this.deviceInfo.isDesktop) {
            // تحسينات لأجهزة سطح المكتب
            document.body.classList.add('desktop-optimized');
            
            // تفعيل الرسوم المتحركة المتقدمة
            document.body.classList.add('enhanced-animations');
        }

        if (this.deviceInfo.pixelRatio > 2) {
            // تحسينات للشاشات عالية الدقة
            document.body.classList.add('high-dpi');
        }
    }
}

// تهيئة النظام عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', () => {
    window.deviceCompatibility = new DeviceCompatibility();
    
    // إضافة الأدوات المساعدة للنافذة العامة
    window.getDeviceInfo = () => window.deviceCompatibility.getDeviceInfo();
    window.supportsFeature = (feature) => window.deviceCompatibility.supportsFeature(feature);
});

// تصدير الفئة للاستخدام في ملفات أخرى
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DeviceCompatibility;
}

