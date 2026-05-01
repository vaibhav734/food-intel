import 'package:flutter/foundation.dart';
import 'models.dart';
import 'api_client.dart';
import 'off_client.dart';

enum AnalysisStatus { idle, loading, success, error }

class AnalysisProvider extends ChangeNotifier {
  AnalysisStatus status = AnalysisStatus.idle;
  AnalyzeResponse? result;
  String? errorMessage;

  Future<void> analyze(AnalyzeRequest req) async {
    _setLoading();
    try {
      result = await ApiClient.analyze(req);
      status = AnalysisStatus.success;
    } catch (e) {
      _setError(e);
    }
    notifyListeners();
  }

  /// Barcode scan flow:
  /// 1. Try Open Food Facts → build AnalyzeRequest with full nutrition data
  /// 2. If OFF has the product → send to our backend for scoring
  /// 3. If OFF misses it → fall back to our backend's barcode lookup
  Future<void> scanBarcode(String barcode) async {
    _setLoading();
    try {
      final offReq = await OffClient.lookup(barcode);
      if (offReq != null) {
        result = await ApiClient.analyze(offReq);
      } else {
        result = await ApiClient.lookupBarcode(barcode);
      }
      status = AnalysisStatus.success;
    } catch (e) {
      _setError(e);
    }
    notifyListeners();
  }

  void reset() {
    status = AnalysisStatus.idle;
    result = null;
    errorMessage = null;
    notifyListeners();
  }

  void _setLoading() {
    status = AnalysisStatus.loading;
    result = null;
    errorMessage = null;
    notifyListeners();
  }

  void _setError(Object e) {
    errorMessage = e.toString();
    status = AnalysisStatus.error;
  }
}
