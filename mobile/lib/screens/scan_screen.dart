import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:provider/provider.dart';
import '../analysis_provider.dart';
import '../off_client.dart';
import 'entry_screen.dart';

class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key});

  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> {
  bool _processing = false;

  void _onDetect(BarcodeCapture capture) async {
    if (_processing) return;
    final barcode = capture.barcodes.firstOrNull?.rawValue;
    if (barcode == null) return;

    setState(() => _processing = true);

    // Try OFF prefill first — shows form with data pre-filled for review
    final offReq = await OffClient.lookup(barcode);

    if (!mounted) return;

    if (offReq != null) {
      // Navigate to entry screen with pre-filled data
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => EntryScreen(prefill: offReq),
        ),
      );
    } else {
      // OFF miss — fall back to direct backend barcode lookup
      await context.read<AnalysisProvider>().scanBarcode(barcode);
      if (mounted) Navigator.pushReplacementNamed(context, '/result');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scan Barcode')),
      body: Stack(
        children: [
          MobileScanner(onDetect: _onDetect),
          Center(
            child: Container(
              width: 260,
              height: 260,
              decoration: BoxDecoration(
                border: Border.all(color: Colors.green, width: 3),
                borderRadius: BorderRadius.circular(12),
              ),
            ),
          ),
          if (_processing)
            const Center(child: CircularProgressIndicator()),
        ],
      ),
    );
  }
}
