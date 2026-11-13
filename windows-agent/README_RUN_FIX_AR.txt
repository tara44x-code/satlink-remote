اصلاح تشغيل Windows Agent

اذا ظهر خطأ غريب مثل:
'cho' is not recognized
او اوامر ناقصة داخل run.bat
فهذا بسبب تلف ترميز ملف التشغيل او مسار مجلد فيه رموز غريبة.

الحل:
1. فك الضغط داخل مسار إنجليزي قصير مثل:
   C:\SatLinkRemotePRO

2. افتح:
   C:\SatLinkRemotePRO\SatLinkRemotePRO\windows-agent

3. شغل واحد من هذه الملفات:
   run.bat        = يختار Python 3.12 او 3.11 تلقائياً
   run_py311.bat  = يجبر التشغيل على Python 3.11
   run_py312.bat  = يجبر التشغيل على Python 3.12

مهم:
- لا تستخدم Python 3.14 لهذه النسخة.
- ثبت Python 3.11 او 3.12 مع خيار Add python.exe to PATH.
- لا تضع المشروع داخل مجلد اسمه عربي او يحتوي رموز غريبة.
