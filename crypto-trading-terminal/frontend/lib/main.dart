import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:window_manager/window_manager.dart';

import 'src/presentation/pages/home/home_page.dart';
import 'src/presentation/pages/strategies/condition_builder_page.dart';
import 'src/presentation/pages/strategies/condition_monitor_page.dart';
import 'src/presentation/pages/strategies/auto_order_config_page.dart';
import 'src/presentation/pages/order_history/order_history_page.dart';
import 'src/presentation/pages/risk_control/risk_control_dashboard.dart';
import 'src/presentation/theme/app_theme.dart';
import 'src/presentation/providers/market/market_data_provider.dart';

void main() async {
  // 确保Flutter绑定初始化
  WidgetsFlutterBinding.ensureInitialized();
  
  // 初始化桌面窗口管理器
  await windowManager.ensureInitialized();
  
  // 配置窗口属性
  const windowOptions = WindowOptions(
    size: Size(1400, 900),
    minimumSize: Size(1200, 800),
    center: true,
    backgroundColor: Colors.transparent,
    skipTaskbar: false,
    titleBarStyle: TitleBarStyle.normal,
    windowButtonVisibility: true,
  );
  
  windowManager.waitUntilReadyToShow(windowOptions, () async {
    await windowManager.show();
    await windowManager.focus();
  });
  
  // 启动应用
  runApp(
    const ProviderScope(
      child: CryptoTradingApp(),
    ),
  );
}

class CryptoTradingApp extends ConsumerWidget {
  const CryptoTradingApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp(
      title: '加密货币专业交易终端',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: ThemeMode.system,
      home: const HomePage(),
      
      // 路由配置
      onGenerateRoute: _generateRoute,
      
      // 本地化支持
      locale: const Locale('zh', 'CN'),
      
      // 错误处理
      builder: (context, child) {
        ErrorWidget.builder = (FlutterErrorDetails details) {
          return Container(
            padding: const EdgeInsets.all(20),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(
                  Icons.error_outline,
                  size: 64,
                  color: Colors.red,
                ),
                const SizedBox(height: 16),
                Text(
                  '抱歉，应用出现了错误',
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
                const SizedBox(height: 8),
                Text(
                  details.exception.toString(),
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontFamily: 'monospace',
                  ),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          );
        };
        return child ?? const SizedBox.shrink();
      },
    );
  }
  
  Route<dynamic>? _generateRoute(RouteSettings settings) {
    switch (settings.name) {
      case '/conditions':
        return MaterialPageRoute(
          builder: (context) => const ConditionBuilderPage(),
        );
      case '/condition-monitor':
        return MaterialPageRoute(
          builder: (context) => const ConditionMonitorPage(),
        );
      case '/auto-orders':
        return MaterialPageRoute(
          builder: (context) => const AutoOrderConfigPage(),
        );
      case '/order-history':
        return MaterialPageRoute(
          builder: (context) => const OrderHistoryPage(),
        );
      case '/risk-control':
        return MaterialPageRoute(
          builder: (context) => const RiskControlDashboardPage(),
        );
      default:
        return null;
    }
  }
}