import 'dart:convert';
import 'package:http/http.dart' as http;
import 'models.dart';

class OffClient {
  static const _base = 'https://world.openfoodfacts.org/api/v2/product';
  static const _fields =
      'product_name,code,nutriments,ingredients_text,nova_group,categories_tags';

  /// Returns an [AnalyzeRequest] pre-filled from Open Food Facts, or null if
  /// the product is not found / the response is unusable.
  static Future<AnalyzeRequest?> lookup(String barcode) async {
    final uri = Uri.parse('$_base/$barcode.json?fields=$_fields');
    final res = await http.get(uri, headers: {
      'User-Agent': 'FoodIntelApp/1.0 (contact@foodintel.app)',
    });

    if (res.statusCode != 200) return null;

    final body = jsonDecode(res.body) as Map<String, dynamic>;
    if ((body['status'] as int?) != 1) return null; // product not found

    final p = body['product'] as Map<String, dynamic>;
    final n = (p['nutriments'] as Map<String, dynamic>?) ?? {};

    double? nutrientValue(String key) {
      final v = n[key];
      if (v == null) return null;
      return (v as num).toDouble();
    }

    final categories =
        (p['categories_tags'] as List?)?.map((e) => e.toString()).toList() ??
            [];
    final isBaby = categories.any((c) =>
        c.contains('baby') || c.contains('infant') || c.contains('toddler'));

    return AnalyzeRequest(
      name: (p['product_name'] as String?)?.trim() ?? barcode,
      barcode: barcode,
      nutrition: NutritionInput(
        caloriesKcal: nutrientValue('energy-kcal_100g'),
        sugarG: nutrientValue('sugars_100g'),
        saturatedFatG: nutrientValue('saturated-fat_100g'),
        sodiumMg: nutrientValue('sodium_100g') != null
            ? nutrientValue('sodium_100g')! * 1000
            : null,
        proteinG: nutrientValue('proteins_100g'),
        fiberG: nutrientValue('fiber_100g'),
      ),
      ingredientsRaw: (p['ingredients_text'] as String?)?.trim(),
      novaClass: p['nova_group'] as int?,
      productType: isBaby ? 'baby_food' : 'food',
    );
  }
}
