import 'package:flutter/material.dart';

/// 浮动操作按钮Widget
/// 提供统一风格的浮动操作按钮
class FloatingActionButtonWidget extends StatelessWidget {
  final VoidCallback? onPressed;
  final IconData icon;
  final String? label;
  final String? tooltip;
  final Color? backgroundColor;
  final Color? foregroundColor;
  final double? iconSize;
  final FloatingActionButtonSize size;

  const FloatingActionButtonWidget({
    super.key,
    required this.onPressed,
    required this.icon,
    this.label,
    this.tooltip,
    this.backgroundColor,
    this.foregroundColor,
    this.iconSize,
    this.size = FloatingActionButtonSize.normal,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final fabSize = _getFABSize(size);
    
    if (label != null) {
      // 带标签的FAB
      return Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              backgroundColor ?? theme.colorScheme.primary,
              (backgroundColor ?? theme.colorScheme.primary).withOpacity(0.8),
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(fabSize),
          boxShadow: [
            BoxShadow(
              color: (backgroundColor ?? theme.colorScheme.primary).withOpacity(0.3),
              blurRadius: 8,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: onPressed,
            borderRadius: BorderRadius.circular(fabSize),
            child: Container(
              padding: const EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 12,
              ),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(fabSize),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    icon,
                    color: foregroundColor ?? Colors.white,
                    size: iconSize ?? 24,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    label!,
                    style: TextStyle(
                      color: foregroundColor ?? Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    } else {
      // 标准FAB
      return FloatingActionButton(
        onPressed: onPressed,
        backgroundColor: backgroundColor ?? theme.colorScheme.primary,
        foregroundColor: foregroundColor ?? theme.colorScheme.onPrimary,
        tooltip: tooltip,
        child: Icon(
          icon,
          size: iconSize ?? 24,
        ),
      );
    }
  }

  double _getFABSize(FloatingActionButtonSize size) {
    switch (size) {
      case FloatingActionButtonSize.small:
        return 40;
      case FloatingActionButtonSize.normal:
        return 56;
      case FloatingActionButtonSize.large:
        return 64;
    }
  }
}

/// FAB尺寸枚举
enum FloatingActionButtonSize {
  small,
  normal,
  large,
}

/// 迷你FAB Widget
class MiniFloatingActionButtonWidget extends StatelessWidget {
  final VoidCallback? onPressed;
  final IconData icon;
  final String? tooltip;
  final Color? backgroundColor;
  final Color? foregroundColor;
  final double? iconSize;

  const MiniFloatingActionButtonWidget({
    super.key,
    required this.onPressed,
    required this.icon,
    this.tooltip,
    this.backgroundColor,
    this.foregroundColor,
    this.iconSize,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return FloatingActionButton(
      onPressed: onPressed,
      backgroundColor: backgroundColor ?? theme.colorScheme.secondary,
      foregroundColor: foregroundColor ?? theme.colorScheme.onSecondary,
      tooltip: tooltip,
      mini: true,
      child: Icon(
        icon,
        size: iconSize ?? 20,
      ),
    );
  }
}

/// FAB组 Widget
/// 包含多个FAB的组合
class FloatingActionButtonGroupWidget extends StatelessWidget {
  final List<FABItem> items;
  final FloatingActionButtonLocation location;

  const FloatingActionButtonGroupWidget({
    super.key,
    required this.items,
    this.location = FloatingActionButtonLocation.endFloat,
  });

  @override
  Widget build(BuildContext context) {
    // 这里提供一个简化的实现
    // 完整的FloatingActionButton组需要更复杂的动画逻辑
    if (items.length == 1) {
      return FloatingActionButtonWidget(
        onPressed: items.first.onPressed,
        icon: items.first.icon,
        label: items.first.label,
        tooltip: items.first.tooltip,
        backgroundColor: items.first.backgroundColor,
      );
    }
    
    // 对于多个FAB，这里使用简单的Column布局
    // 实际应用中可能需要使用Animation和GestureDetector实现更复杂的效果
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: items.map((item) {
        return Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: FloatingActionButtonWidget(
            onPressed: item.onPressed,
            icon: item.icon,
            label: item.label,
            tooltip: item.tooltip,
            backgroundColor: item.backgroundColor,
            size: FloatingActionButtonSize.small,
          ),
        );
      }).toList(),
    );
  }
}

/// FAB项目定义
class FABItem {
  final VoidCallback? onPressed;
  final IconData icon;
  final String? label;
  final String? tooltip;
  final Color? backgroundColor;

  const FABItem({
    required this.onPressed,
    required this.icon,
    this.label,
    this.tooltip,
    this.backgroundColor,
  });
}

/// 扩展的FAB位置
extension FABLocationExtension on FloatingActionButtonLocation {
  bool get isBottom => [
    FloatingActionButtonLocation.centerFloat,
    FloatingActionButtonLocation.endFloat,
    FloatingActionButtonLocation.startFloat,
  ].contains(this);
  
  bool get isCenter => this == FloatingActionButtonLocation.centerFloat;
  bool get isEnd => this == FloatingActionButtonLocation.endFloat;
  bool get isStart => this == FloatingActionButtonLocation.startFloat;
}
