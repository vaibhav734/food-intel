// API contract types mirroring backend schemas.py

class NutritionInput {
  final double? caloriesKcal;
  final double? sugarG;
  final double? saturatedFatG;
  final double? sodiumMg;
  final double? proteinG;
  final double? fiberG;
  final double? servingSizeG;

  const NutritionInput({
    this.caloriesKcal,
    this.sugarG,
    this.saturatedFatG,
    this.sodiumMg,
    this.proteinG,
    this.fiberG,
    this.servingSizeG,
  });

  factory NutritionInput.fromJson(Map<String, dynamic> j) => NutritionInput(
        caloriesKcal: (j['calories_kcal'] as num?)?.toDouble(),
        sugarG: (j['sugar_g'] as num?)?.toDouble(),
        saturatedFatG: (j['saturated_fat_g'] as num?)?.toDouble(),
        sodiumMg: (j['sodium_mg'] as num?)?.toDouble(),
        proteinG: (j['protein_g'] as num?)?.toDouble(),
        fiberG: (j['fiber_g'] as num?)?.toDouble(),
        servingSizeG: (j['serving_size_g'] as num?)?.toDouble(),
      );

  Map<String, dynamic> toJson() => {
        if (caloriesKcal != null) 'calories_kcal': caloriesKcal,
        if (sugarG != null) 'sugar_g': sugarG,
        if (saturatedFatG != null) 'saturated_fat_g': saturatedFatG,
        if (sodiumMg != null) 'sodium_mg': sodiumMg,
        if (proteinG != null) 'protein_g': proteinG,
        if (fiberG != null) 'fiber_g': fiberG,
        if (servingSizeG != null) 'serving_size_g': servingSizeG,
      };
}

class AnalyzeRequest {
  final String name;
  final String? barcode;
  final NutritionInput nutrition;
  final String? ingredientsRaw;
  final int? novaClass;
  final String productType; // "food" | "baby_food" | "cosmetic"
  final int? minAgeMonths;
  final int? maxAgeMonths;

  const AnalyzeRequest({
    required this.name,
    this.barcode,
    this.nutrition = const NutritionInput(),
    this.ingredientsRaw,
    this.novaClass,
    this.productType = 'food',
    this.minAgeMonths,
    this.maxAgeMonths,
  });

  Map<String, dynamic> toJson() => {
        'name': name,
        if (barcode != null) 'barcode': barcode,
        'nutrition': nutrition.toJson(),
        if (ingredientsRaw != null) 'ingredients_raw': ingredientsRaw,
        if (novaClass != null) 'nova_class': novaClass,
        'product_type': productType,
        if (minAgeMonths != null) 'min_age_months': minAgeMonths,
        if (maxAgeMonths != null) 'max_age_months': maxAgeMonths,
      };
}

class AgeSafety {
  final int? minAgeMonths;
  final int? maxAgeMonths;
  final String label;
  final bool safe;

  const AgeSafety({
    this.minAgeMonths,
    this.maxAgeMonths,
    required this.label,
    required this.safe,
  });

  factory AgeSafety.fromJson(Map<String, dynamic> j) => AgeSafety(
        minAgeMonths: j['min_age_months'] as int?,
        maxAgeMonths: j['max_age_months'] as int?,
        label: j['label'] as String,
        safe: j['safe'] as bool,
      );
}

class Reason {
  final String ruleId;
  final String text;
  final double delta;
  final String sourceOrg;

  const Reason({
    required this.ruleId,
    required this.text,
    required this.delta,
    required this.sourceOrg,
  });

  factory Reason.fromJson(Map<String, dynamic> j) => Reason(
        ruleId: j['rule_id'] as String,
        text: j['text'] as String,
        delta: (j['delta'] as num).toDouble(),
        sourceOrg: (j['source'] as Map<String, dynamic>)['org'] as String,
      );
}

class ScoringResult {
  final int score;
  final String verdict;
  final String confidence;
  final List<Reason> reasons;
  final List<String> missingFields;
  final AgeSafety? ageSafety;
  final bool dataUnavailable;

  const ScoringResult({
    required this.score,
    required this.verdict,
    required this.confidence,
    required this.reasons,
    required this.missingFields,
    this.ageSafety,
    this.dataUnavailable = false,
  });

  factory ScoringResult.fromJson(Map<String, dynamic> j) => ScoringResult(
        score: j['score'] as int,
        verdict: j['verdict'] as String,
        confidence: j['confidence'] as String,
        reasons: (j['reasons'] as List)
            .map((r) => Reason.fromJson(r as Map<String, dynamic>))
            .toList(),
        missingFields: List<String>.from(j['missing_fields'] as List),
        ageSafety: j['age_safety'] != null
            ? AgeSafety.fromJson(j['age_safety'] as Map<String, dynamic>)
            : null,
        dataUnavailable: j['data_unavailable'] as bool? ?? false,
      );
}

class AnalyzeResponse {
  final String productName;
  final String? barcode;
  final ScoringResult scoring;
  final String explanation;
  final NutritionInput nutrition;

  const AnalyzeResponse({
    required this.productName,
    this.barcode,
    required this.scoring,
    required this.explanation,
    this.nutrition = const NutritionInput(),
  });

  factory AnalyzeResponse.fromJson(Map<String, dynamic> j) => AnalyzeResponse(
        productName: j['product_name'] as String,
        barcode: j['barcode'] as String?,
        scoring: ScoringResult.fromJson(j['scoring'] as Map<String, dynamic>),
        explanation: j['explanation'] as String,
        nutrition: j['nutrition'] != null
            ? NutritionInput.fromJson(j['nutrition'] as Map<String, dynamic>)
            : const NutritionInput(),
      );
}
