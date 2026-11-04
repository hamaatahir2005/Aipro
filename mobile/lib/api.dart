import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
class Api {
  final String base;
  final storage = const FlutterSecureStorage();
  Api({this.base = const String.fromEnvironment('API_URL', defaultValue: 'http://10.0.2.2:8000')});
  Future<dynamic> call(String path, {Map<String, dynamic>? body, bool retry = true}) async {
    final token = await storage.read(key: 'access');
    final headers = {'Content-Type':'application/json', if (token != null) 'Authorization':'Bearer $token'};
    final uri = Uri.parse('$base$path');
    final response = await (body == null ? http.get(uri, headers: headers) : http.post(uri, headers: headers, body: jsonEncode(body))).timeout(const Duration(seconds: 200));
    if (response.statusCode == 401 && retry && !path.startsWith('/auth/')) {
      final refresh = await storage.read(key:'refresh');
      if (refresh != null) {
        final tokens = await call('/auth/refresh', body: {'refresh_token':refresh}, retry: false);
        await saveTokens(tokens);
        return call(path, body:body, retry:false);
      }
    }
    final data = jsonDecode(response.body);
    if (response.statusCode >= 400) throw Exception(data['detail'] ?? 'Request failed (${response.statusCode})');
    return data;
  }
  Future<void> saveTokens(dynamic data) async {
    await storage.write(key:'access',value:data['access_token']);
    await storage.write(key:'refresh',value:data['refresh_token']);
  }
}
