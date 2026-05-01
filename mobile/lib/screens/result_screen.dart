import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../analysis_provider.dart';
import '../models.dart';

class ResultScreen extends StatelessWidget {
  const ResultScreen({super.key});

  Color _scoreColor(int score) {
    if (score >= 7) return Colors.green;
    if (score >= 4) return Colors.orange;
    return Colors.red;
  }

  Color _confidenceColor(String confidence) {
    switch (confidence) {
      case 'high':
        return Colors.green;
      case 'medium':
        return Colors.orange;
      default:
        return Colors.red;
    }
  }

  String _ageLabel(int months) {
    if (months < 12) return '${months}m';
    final years = months ~/ 12;
    final remMonths = months % 12;
    if (remMonths == 0) return '${years}y';
    return '${years}y ${remMonths}m';
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<AnalysisProvider>();

    if (provider.status == AnalysisStatus.loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    if (provider.status == AnalysisStatus.error) {
      return Scaffold(
        appBar: AppBar(title: const Text('Error')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.error_outline, size: 64, color: Colors.red),
                const SizedBox(height: 16),
                Text(provider.errorMessage ?? 'Unknown error',
                    textAlign: TextAlign.center),
                const SizedBox(height: 24),
                ElevatedButton(
                  onPressed: () {
                    provider.reset();
                    Navigator.pop(context);
                  },
                  child: const Text('Try Again'),
                ),
              ],
            ),
          ),
        ),
      );
    }

    final result = provider.result!;
    final scoring = result.scoring;

    return Scaffold(
      appBar: AppBar(
        title: Text(result.productName, overflow: TextOverflow.ellipsis),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              provider.reset();
              Navigator.pop(context);
            },
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Score card
            Card(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: scoring.dataUnavailable
                    ? const Row(
                        children: [
                          CircleAvatar(
                            radius: 36,
                            backgroundColor: Colors.grey,
                            child: Text('N/A',
                                style: TextStyle(
                                    fontSize: 18,
                                    fontWeight: FontWeight.bold,
                                    color: Colors.white)),
                          ),
                          SizedBox(width: 16),
                          Expanded(
                            child: Text(
                              'Insufficient data to score this product.\nNo nutrition information is available.',
                              style: TextStyle(fontSize: 14),
                            ),
                          ),
                        ],
                      )
                    : Row(
                        children: [
                          CircleAvatar(
                            radius: 36,
                            backgroundColor: _scoreColor(scoring.score),
                            child: Text(
                              '${scoring.score}',
                              style: const TextStyle(
                                  fontSize: 28,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.white),
                            ),
                          ),
                          const SizedBox(width: 16),
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(scoring.verdict,
                                  style: Theme.of(context)
                                      .textTheme
                                      .headlineSmall),
                              const SizedBox(height: 4),
                              Chip(
                                label: Text(
                                    '${scoring.confidence.toUpperCase()} confidence'),
                                backgroundColor:
                                    _confidenceColor(scoring.confidence)
                                        .withValues(alpha: 0.15),
                                labelStyle: TextStyle(
                                    color: _confidenceColor(scoring.confidence),
                                    fontWeight: FontWeight.w600),
                              ),
                            ],
                          ),
                        ],
                      ),
              ),
            ),

            // Age safety (baby products)
            if (scoring.ageSafety != null) ...[
              const SizedBox(height: 12),
              Card(
                color: scoring.ageSafety!.safe
                    ? Colors.green.shade50
                    : Colors.red.shade50,
                child: ListTile(
                  leading: Icon(
                    scoring.ageSafety!.safe
                        ? Icons.child_care
                        : Icons.warning_amber,
                    color: scoring.ageSafety!.safe ? Colors.green : Colors.red,
                  ),
                  title: Text(scoring.ageSafety!.label),
                  subtitle: Text(
                    [
                      if (scoring.ageSafety!.minAgeMonths != null ||
                          scoring.ageSafety!.maxAgeMonths != null)
                        'Age range: ${scoring.ageSafety!.minAgeMonths != null ? _ageLabel(scoring.ageSafety!.minAgeMonths!) : '0m'} - ${scoring.ageSafety!.maxAgeMonths != null ? _ageLabel(scoring.ageSafety!.maxAgeMonths!) : 'any older age'}',
                      if (!scoring.ageSafety!.safe)
                        'Contains ingredients restricted for this age group',
                    ].join('\n'),
                  ),
                ),
              ),
            ],

            const SizedBox(height: 16),
            _NutritionCard(nutrition: result.nutrition),

            // Missing data warning
            if (scoring.missingFields.isNotEmpty) ...[
              const SizedBox(height: 12),
              Card(
                color: Colors.amber.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.info_outline, color: Colors.amber),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Score limited by missing data: ${scoring.missingFields.join(', ')}',
                          style: const TextStyle(fontSize: 13),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],

            // Explanation
            const SizedBox(height: 16),
            Text('Summary', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text(result.explanation),

            // Reasons
            const SizedBox(height: 16),
            Text('Why this score?',
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            ...scoring.reasons.map((r) => _ReasonTile(reason: r)),
          ],
        ),
      ),
    );
  }
}

class _ReasonTile extends StatelessWidget {
  final Reason reason;
  const _ReasonTile({required this.reason});

  @override
  Widget build(BuildContext context) {
    final isBonus = reason.delta > 0;
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: Icon(
        isBonus ? Icons.add_circle_outline : Icons.remove_circle_outline,
        color: isBonus ? Colors.green : Colors.red,
      ),
      title: Text(reason.text, style: const TextStyle(fontSize: 14)),
      subtitle: Text('Source: ${reason.sourceOrg}',
          style: const TextStyle(fontSize: 12, color: Colors.grey)),
      trailing: Text(
        '${isBonus ? '+' : ''}${reason.delta.toStringAsFixed(1)}',
        style: TextStyle(
            color: isBonus ? Colors.green : Colors.red,
            fontWeight: FontWeight.bold),
      ),
    );
  }
}

class _NutrientDef {
  final String label;
  final String unit;
  final double max;
  final double low;
  final double high;
  final bool lowerIsBetter;
  final IconData icon;

  const _NutrientDef({
    required this.label,
    required this.unit,
    required this.max,
    required this.low,
    required this.high,
    required this.lowerIsBetter,
    required this.icon,
  });
}

class _NutrientViewData {
  final double? value;
  final Color color;
  final String status;
  final double fraction;

  const _NutrientViewData({
    required this.value,
    required this.color,
    required this.status,
    required this.fraction,
  });
}

class _NutritionCard extends StatelessWidget {
  final NutritionInput nutrition;

  const _NutritionCard({required this.nutrition});

  static const Map<String, _NutrientDef> _defs = {
    'calories': _NutrientDef(
      label: 'Calories',
      unit: 'kcal',
      max: 600,
      low: 150,
      high: 400,
      lowerIsBetter: true,
      icon: Icons.local_fire_department_outlined,
    ),
    'sugar': _NutrientDef(
      label: 'Sugar',
      unit: 'g',
      max: 50,
      low: 5,
      high: 22,
      lowerIsBetter: true,
      icon: Icons.cake_outlined,
    ),
    'satFat': _NutrientDef(
      label: 'Saturated fat',
      unit: 'g',
      max: 20,
      low: 1.5,
      high: 5,
      lowerIsBetter: true,
      icon: Icons.opacity_outlined,
    ),
    'sodium': _NutrientDef(
      label: 'Sodium',
      unit: 'mg',
      max: 1500,
      low: 120,
      high: 600,
      lowerIsBetter: true,
      icon: Icons.grain_outlined,
    ),
    'protein': _NutrientDef(
      label: 'Protein',
      unit: 'g',
      max: 30,
      low: 5,
      high: 10,
      lowerIsBetter: false,
      icon: Icons.fitness_center_outlined,
    ),
    'fiber': _NutrientDef(
      label: 'Fiber',
      unit: 'g',
      max: 15,
      low: 1.5,
      high: 3,
      lowerIsBetter: false,
      icon: Icons.spa_outlined,
    ),
  };

  _NutrientViewData _classify(_NutrientDef def, double? value) {
    if (value == null) {
      return const _NutrientViewData(
        value: null,
        color: Colors.grey,
        status: 'No data',
        fraction: 0,
      );
    }

    if (def.lowerIsBetter) {
      if (value <= def.low) {
        return _NutrientViewData(
          value: value,
          color: Colors.green.shade600,
          status: 'Low',
          fraction: (value / def.max).clamp(0, 1),
        );
      }
      if (value <= def.high) {
        return _NutrientViewData(
          value: value,
          color: Colors.orange.shade700,
          status: 'Medium',
          fraction: (value / def.max).clamp(0, 1),
        );
      }
      return _NutrientViewData(
        value: value,
        color: Colors.red.shade600,
        status: 'High',
        fraction: (value / def.max).clamp(0, 1),
      );
    }

    if (value >= def.high) {
      return _NutrientViewData(
        value: value,
        color: Colors.green.shade600,
        status: 'Good',
        fraction: (value / def.max).clamp(0, 1),
      );
    }
    if (value >= def.low) {
      return _NutrientViewData(
        value: value,
        color: Colors.orange.shade700,
        status: 'Moderate',
        fraction: (value / def.max).clamp(0, 1),
      );
    }
    return _NutrientViewData(
      value: value,
      color: Colors.red.shade600,
      status: 'Low',
      fraction: (value / def.max).clamp(0, 1),
    );
  }

  String _formatValue(double value) {
    if (value == value.roundToDouble()) {
      return value.toStringAsFixed(0);
    }
    return value.toStringAsFixed(1);
  }

  @override
  Widget build(BuildContext context) {
    final items = <MapEntry<_NutrientDef, double?>>[
      MapEntry(_defs['calories']!, nutrition.caloriesKcal),
      MapEntry(_defs['sugar']!, nutrition.sugarG),
      MapEntry(_defs['satFat']!, nutrition.saturatedFatG),
      MapEntry(_defs['sodium']!, nutrition.sodiumMg),
      MapEntry(_defs['protein']!, nutrition.proteinG),
      MapEntry(_defs['fiber']!, nutrition.fiberG),
    ];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Nutrition per 100g',
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 4),
            Text(
              'Simple view: green is better, amber is mixed, red needs attention.',
              style: Theme.of(context)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: Colors.grey.shade700),
            ),
            const SizedBox(height: 12),
            ...items.map((item) {
              final def = item.key;
              final view = _classify(def, item.value);
              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(def.icon, size: 18, color: view.color),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            def.label,
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                        ),
                        if (view.value != null)
                          Text(
                            '${_formatValue(view.value!)} ${def.unit}',
                            style: TextStyle(
                              color: view.color,
                              fontWeight: FontWeight.w600,
                            ),
                          )
                        else
                          const Text(
                            'No data',
                            style: TextStyle(color: Colors.grey),
                          ),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: view.color.withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(999),
                          ),
                          child: Text(
                            view.status,
                            style: TextStyle(
                              color: view.color,
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(999),
                      child: LinearProgressIndicator(
                        value: view.fraction,
                        minHeight: 10,
                        backgroundColor: Colors.grey.shade300,
                        valueColor: AlwaysStoppedAnimation<Color>(view.color),
                      ),
                    ),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }
}
