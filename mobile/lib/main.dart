import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'analysis_provider.dart';
import 'screens/scan_screen.dart';
import 'screens/entry_screen.dart';
import 'screens/result_screen.dart';

void main() {
  runApp(
    ChangeNotifierProvider(
      create: (_) => AnalysisProvider(),
      child: const FoodIntelApp(),
    ),
  );
}

class FoodIntelApp extends StatelessWidget {
  const FoodIntelApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Food Intel',
      theme: ThemeData(
        colorSchemeSeed: Colors.green,
        useMaterial3: true,
      ),
      initialRoute: '/',
      routes: {
        '/': (_) => const HomeScreen(),
        '/scan': (_) => const ScanScreen(),
        '/entry': (_) => const EntryScreen(),
        '/result': (_) => const ResultScreen(),
      },
    );
  }
}

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Food Intelligence')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.qr_code_scanner, size: 80, color: Colors.green),
              const SizedBox(height: 24),
              const Text(
                'Evidence-based product scoring',
                style: TextStyle(fontSize: 18),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 40),
              FilledButton.icon(
                icon: const Icon(Icons.qr_code_scanner),
                label: const Text('Scan Barcode'),
                onPressed: () => Navigator.pushNamed(context, '/scan'),
              ),
              const SizedBox(height: 16),
              OutlinedButton.icon(
                icon: const Icon(Icons.edit),
                label: const Text('Enter Manually'),
                onPressed: () => Navigator.pushNamed(context, '/entry'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
