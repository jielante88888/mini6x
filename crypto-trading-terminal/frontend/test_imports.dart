// 测试导入验证文件
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

// 导入新创建的Widget
import 'src/presentation/providers/conditions_provider.dart';
import 'src/presentation/pages/strategies/condition_builder_page.dart';
import 'src/presentation/pages/strategies/condition_form_widget.dart';
import 'src/presentation/pages/strategies/condition_card_widget.dart';
import 'src/presentation/widgets/common/app_bar_widget.dart';
import 'src/presentation/widgets/common/loading_widget.dart';
import 'src/presentation/widgets/common/error_widget.dart';
import 'src/presentation/widgets/common/floating_action_button_widget.dart';

// 简单的测试Widget
class TestWidget extends ConsumerWidget {
  const TestWidget({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return const Scaffold(
      body: Center(
        child: Text('All imports successful'),
      ),
    );
  }
}

void main() {
  runApp(const MaterialApp(
    home: TestWidget(),
  ));
}
