import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../analysis_provider.dart';
import '../models.dart';

class EntryScreen extends StatefulWidget {
  final AnalyzeRequest? prefill;
  const EntryScreen({super.key, this.prefill});

  @override
  State<EntryScreen> createState() => _EntryScreenState();
}

class _EntryScreenState extends State<EntryScreen> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _nameCtrl;
  late final TextEditingController _ingredientsCtrl;
  late final TextEditingController _sugarCtrl;
  late final TextEditingController _satFatCtrl;
  late final TextEditingController _sodiumCtrl;
  late final TextEditingController _proteinCtrl;
  late final TextEditingController _fiberCtrl;
  late String _productType;

  @override
  void initState() {
    super.initState();
    final p = widget.prefill;
    _nameCtrl = TextEditingController(text: p?.name ?? '');
    _ingredientsCtrl = TextEditingController(text: p?.ingredientsRaw ?? '');
    _sugarCtrl = TextEditingController(text: _fmt(p?.nutrition.sugarG));
    _satFatCtrl = TextEditingController(text: _fmt(p?.nutrition.saturatedFatG));
    _sodiumCtrl = TextEditingController(text: _fmt(p?.nutrition.sodiumMg));
    _proteinCtrl = TextEditingController(text: _fmt(p?.nutrition.proteinG));
    _fiberCtrl = TextEditingController(text: _fmt(p?.nutrition.fiberG));
    _productType = p?.productType ?? 'food';
  }

  String _fmt(double? v) =>
      v != null ? v.toStringAsFixed(v.truncateToDouble() == v ? 0 : 1) : '';

  @override
  void dispose() {
    for (final c in [
      _nameCtrl,
      _ingredientsCtrl,
      _sugarCtrl,
      _satFatCtrl,
      _sodiumCtrl,
      _proteinCtrl,
      _fiberCtrl
    ]) {
      c.dispose();
    }
    super.dispose();
  }

  double? _parse(TextEditingController c) =>
      c.text.trim().isEmpty ? null : double.tryParse(c.text.trim());

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    final req = AnalyzeRequest(
      name: _nameCtrl.text.trim(),
      barcode: widget.prefill?.barcode,
      nutrition: NutritionInput(
        sugarG: _parse(_sugarCtrl),
        saturatedFatG: _parse(_satFatCtrl),
        sodiumMg: _parse(_sodiumCtrl),
        proteinG: _parse(_proteinCtrl),
        fiberG: _parse(_fiberCtrl),
      ),
      ingredientsRaw: _ingredientsCtrl.text.trim().isEmpty
          ? null
          : _ingredientsCtrl.text.trim(),
      novaClass: widget.prefill?.novaClass,
      productType: _productType,
    );
    await context.read<AnalysisProvider>().analyze(req);
    if (mounted) Navigator.pushNamed(context, '/result');
  }

  @override
  Widget build(BuildContext context) {
    final isPrefilled = widget.prefill != null;
    return Scaffold(
      appBar: AppBar(
        title: Text(isPrefilled ? 'Review Product' : 'Enter Product Details'),
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (isPrefilled)
              Container(
                margin: const EdgeInsets.only(bottom: 16),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.green.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.green.shade200),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.check_circle_outline,
                        color: Colors.green, size: 18),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Data fetched from Open Food Facts. Review and tap Analyze.',
                        style: TextStyle(fontSize: 13, color: Colors.green),
                      ),
                    ),
                  ],
                ),
              ),
            TextFormField(
              controller: _nameCtrl,
              decoration: const InputDecoration(labelText: 'Product name *'),
              validator: (v) =>
                  (v == null || v.trim().isEmpty) ? 'Required' : null,
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: _productType,
              decoration: const InputDecoration(labelText: 'Product type'),
              items: const [
                DropdownMenuItem(value: 'food', child: Text('Food')),
                DropdownMenuItem(value: 'baby_food', child: Text('Baby food')),
                DropdownMenuItem(value: 'cosmetic', child: Text('Cosmetic')),
              ],
              onChanged: (v) => setState(() => _productType = v!),
            ),
            const SizedBox(height: 16),
            Text('Nutrition (per 100g)',
                style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 8),
            _NumField(ctrl: _sugarCtrl, label: 'Sugar (g)'),
            _NumField(ctrl: _satFatCtrl, label: 'Saturated fat (g)'),
            _NumField(ctrl: _sodiumCtrl, label: 'Sodium (mg)'),
            _NumField(ctrl: _proteinCtrl, label: 'Protein (g)'),
            _NumField(ctrl: _fiberCtrl, label: 'Fiber (g)'),
            const SizedBox(height: 16),
            TextFormField(
              controller: _ingredientsCtrl,
              decoration: const InputDecoration(
                labelText: 'Ingredients (optional)',
                hintText: 'Paste the ingredient list from the label',
              ),
              maxLines: 3,
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: _submit,
              child: const Text('Analyze'),
            ),
          ],
        ),
      ),
    );
  }
}

class _NumField extends StatelessWidget {
  final TextEditingController ctrl;
  final String label;
  const _NumField({required this.ctrl, required this.label});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: TextFormField(
        controller: ctrl,
        decoration: InputDecoration(labelText: label),
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        validator: (v) {
          if (v == null || v.trim().isEmpty) return null;
          if (double.tryParse(v.trim()) == null) return 'Enter a number';
          if (double.parse(v.trim()) < 0) return 'Must be ≥ 0';
          return null;
        },
      ),
    );
  }
}
