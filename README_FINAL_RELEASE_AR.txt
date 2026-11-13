SatLink Remote PRO FINAL RELEASE PRO 2.1.7

المحتويات:
- START_SATLINK_REMOTE.bat: ملف التشغيل الرئيسي.
- REPAIR_START.bat: ملف إصلاح وتشغيل بديل.
- server/: سيرفر SatLinkRelayServer.
- windows-agent/: برنامج الحاسبة Windows Agent.
- android-app/: مشروع Android Studio للتطبيق.

الحالة الحالية:
- السيرفر يعمل تلقائياً من START_SATLINK_REMOTE.bat.
- البرنامج يفتح بعد السيرفر.
- Relay Client مدمج داخل برنامج الحاسبة.
- نقل الملفات ومدير الملفات موجودان.
- Turbo / Speed Engine موجود.
- الأيقونات الجديدة مثبتة.

للاستخدام الشخصي:
هذه النسخة تعتمد على تشغيل السيرفر محلياً. للاتصال من أي مكان بشكل حقيقي، ارفع مجلد server على VPS أو سيرفر دائم، ثم ضع رابط السيرفر الخارجي داخل التطبيق وبرنامج الحاسبة.

للبناء:
- برنامج الحاسبة EXE:
  windows-agentuild_exe_py311.bat

- سيرفر EXE اختياري:
  serveruild_server_exe_py311.bat

- تطبيق Android APK:
  افتح android-app في Android Studio ثم:
  Build > Build Bundle(s) / APK(s) > Build APK(s)

أمان:
استخدم البرنامج فقط على أجهزتك أو أجهزة لديك إذن واضح للتحكم بها.
