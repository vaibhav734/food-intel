import 'dart:convert';
import 'package:http/http.dart' as http;
import 'config.dart';
import 'models.dart';

class ApiClient {
  static Future<AnalyzeResponse> analyze(AnalyzeRequest req) async {
    final response = await http.post(
      Uri.parse('$kApiBase/analyze'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(req.toJson()),
    );
    if (response.statusCode == 200) {
      return AnalyzeResponse.fromJson(
          jsonDecode(response.body) as Map<String, dynamic>);
    }
    throw Exception('API error ${response.statusCode}');
  }

  static Future<AnalyzeResponse> lookupBarcode(String barcode) async {
    final response = await http.get(Uri.parse('$kApiBase/product/$barcode'));
    if (response.statusCode == 200) {
      return AnalyzeResponse.fromJson(
          jsonDecode(response.body) as Map<String, dynamic>);
    }
    if (response.statusCode == 404) {
      throw Exception('Product not found for barcode $barcode');
    }
    throw Exception('Lookup error ${response.statusCode}');
  }
}
