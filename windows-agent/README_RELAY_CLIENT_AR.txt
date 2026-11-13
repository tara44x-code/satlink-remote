SatLink Remote PRO Relay Client

هذا الملف يربط برنامج الحاسبة بالسيرفر بدون فتح بورت في الراوتر.

قبل تشغيله:
1. شغل برنامج الحاسبة run_py311.bat
2. اضغط تشغيل الاتصال
3. تأكد أن server\relay_server.py يعمل
4. عدل relay_config.json إذا كان عنوان السيرفر مختلفاً
5. شغل run_relay_client_py311.bat

relay_config.json:
relay_server_url = رابط السيرفر
owner_token = نفس الرمز الموجود في server_config.json
local_agent_url = غالباً اتركه http://127.0.0.1:47655
