import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/notification_provider.dart';

/// 通知模板管理Widget
/// 显示和管理不同类型的通知模板
class NotificationTemplatesWidget extends ConsumerWidget {
  const NotificationTemplatesWidget({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final templates = ref.read(notificationProvider.notifier).getAvailableTemplates();

    return Column(
      children: [
        // 模板统计
        _buildTemplatesStats(context, ref),
        
        // 模板列表
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: templates.length,
            itemBuilder: (context, index) {
              final template = templates[index];
              return _buildTemplateCard(context, template, ref);
            },
          ),
        ),
      ],
    );
  }

  /// 构建模板统计
  Widget _buildTemplatesStats(BuildContext context, WidgetRef ref) {
    final notificationState = ref.watch(notificationProvider);
    
    return Container(
      margin: const EdgeInsets.all(16),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              // 模板总数
              Expanded(
                child: _buildStatItem(
                  context,
                  '模板类型',
                  '${templates.length}种',
                  Icons.text_snippet,
                  Colors.blue,
                ),
              ),
              Container(
                width: 1,
                height: 40,
                color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
              ),
              // 启用模板
              Expanded(
                child: _buildStatItem(
                  context,
                  '启用模板',
                  '5个', // TODO: 从设置中读取
                  Icons.check_circle,
                  Colors.green,
                ),
              ),
              Container(
                width: 1,
                height: 40,
                color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
              ),
              // 自定义模板
              Expanded(
                child: _buildStatItem(
                  context,
                  '自定义模板',
                  '2个', // TODO: 从设置中读取
                  Icons.edit,
                  Colors.orange,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// 构建统计项
  Widget _buildStatItem(
    BuildContext context,
    String label,
    String value,
    IconData icon,
    Color color,
  ) {
    return Column(
      children: [
        Icon(icon, color: color, size: 24),
        const SizedBox(height: 4),
        Text(
          value,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: color,
                fontWeight: FontWeight.bold,
              ),
        ),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
              ),
        ),
      ],
    );
  }

  /// 构建模板卡片
  Widget _buildTemplateCard(
    BuildContext context,
    NotificationTemplateType template,
    WidgetRef ref,
  ) {
    final theme = Theme.of(context);
    
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: () => _showTemplateEditor(context, template, ref),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 模板头部
              Row(
                children: [
                  _buildTemplateIcon(template, theme),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Text(
                              template.displayName,
                              style: theme.textTheme.titleMedium?.copyWith(
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(width: 8),
                            _buildEnabledBadge(context, template), // TODO: 从设置中读取
                          ],
                        ),
                        Text(
                          _getTemplateDescription(template),
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.colorScheme.onSurface.withOpacity(0.7),
                          ),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    onPressed: () => _showTemplateEditor(context, template, ref),
                    icon: const Icon(Icons.edit, color: Colors.grey),
                    tooltip: '编辑模板',
                  ),
                ],
              ),
              
              const SizedBox(height: 12),
              
              // 模板预览
              _buildTemplatePreview(template, theme),
              
              const SizedBox(height: 8),
              
              // 模板操作
              _buildTemplateActions(context, template, ref),
            ],
          ),
        ),
      ),
    );
  }

  /// 构建模板图标
  Widget _buildTemplateIcon(NotificationTemplateType template, ThemeData theme) {
    Color iconColor;
    IconData iconData;
    
    switch (template) {
      case NotificationTemplateType.priceAlert:
        iconColor = Colors.green;
        iconData = Icons.attach_money;
        break;
      case NotificationTemplateType.volumeAlert:
        iconColor = Colors.blue;
        iconData = Icons.bar_chart;
        break;
      case NotificationTemplateType.technicalAlert:
        iconColor = Colors.orange;
        iconData = Icons.trending_up;
        break;
      case NotificationTemplateType.emergencyAlert:
        iconColor = Colors.red;
        iconData = Icons.warning;
        break;
      case NotificationTemplateType.custom:
        iconColor = Colors.purple;
        iconData = Icons.edit;
        break;
    }
    
    return Container(
      width: 40,
      height: 40,
      decoration: BoxDecoration(
        color: iconColor.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Icon(
        iconData,
        color: iconColor,
        size: 20,
      ),
    );
  }

  /// 构建启用标签
  Widget _buildEnabledBadge(BuildContext context, NotificationTemplateType template) {
    final isEnabled = true; // TODO: 从设置中读取
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: isEnabled ? Colors.green.withOpacity(0.1) : Colors.grey.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isEnabled ? Colors.green.withOpacity(0.3) : Colors.grey.withOpacity(0.3),
        ),
      ),
      child: Text(
        isEnabled ? '已启用' : '已禁用',
        style: TextStyle(
          color: isEnabled ? Colors.green : Colors.grey,
          fontSize: 12,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }

  /// 获取模板描述
  String _getTemplateDescription(NotificationTemplateType template) {
    switch (template) {
      case NotificationTemplateType.priceAlert:
        return '用于价格达到设定阈值时的通知模板';
      case NotificationTemplateType.volumeAlert:
        return '用于成交量异常时的通知模板';
      case NotificationTemplateType.technicalAlert:
        return '用于技术指标触发的通知模板';
      case NotificationTemplateType.emergencyAlert:
        return '用于紧急情况的警告通知模板';
      case NotificationTemplateType.custom:
        return '用户自定义的通知模板';
    }
  }

  /// 构建模板预览
  Widget _buildTemplatePreview(NotificationTemplateType template, ThemeData theme) {
    final preview = _getTemplatePreview(template);
    
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceVariant.withOpacity(0.3),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '预览:',
            style: theme.textTheme.bodySmall?.copyWith(
              fontWeight: FontWeight.w500,
              color: theme.colorScheme.onSurface.withOpacity(0.7),
            ),
          ),
          const SizedBox(height: 4),
          Text(
            preview,
            style: theme.textTheme.bodyMedium?.copyWith(
              fontFamily: 'monospace',
            ),
            maxLines: 3,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  /// 获取模板预览
  String _getTemplatePreview(NotificationTemplateType template) {
    switch (template) {
      case NotificationTemplateType.priceAlert:
        return '🚨 价格预警 - BTC/USDT\n价格: $50,000.00 (> $45,000.00)\n时间: 2025-11-14 15:30:00';
      case NotificationTemplateType.volumeAlert:
        return '📊 成交量预警 - ETH/USDT\n成交量: 2.5M (> 1M)\n时间: 2025-11-14 15:30:00';
      case NotificationTemplateType.technicalAlert:
        return '📈 技术指标预警 - BTC/USDT\nMACD金叉确认\n时间: 2025-11-14 15:30:00';
      case NotificationTemplateType.emergencyAlert:
        return '🚨 紧急预警 - 系统异常\n交易所连接断开\n时间: 2025-11-14 15:30:00';
      case NotificationTemplateType.custom:
        return '自定义通知模板内容...\n变量: {condition_name}, {result_value}, {trigger_time}';
    }
  }

  /// 构建模板操作
  Widget _buildTemplateActions(
    BuildContext context,
    NotificationTemplateType template,
    WidgetRef ref,
  ) {
    return Row(
      children: [
        // 编辑按钮
        OutlinedButton.icon(
          onPressed: () => _showTemplateEditor(context, template, ref),
          icon: const Icon(Icons.edit, size: 16),
          label: const Text('编辑'),
          style: OutlinedButton.styleFrom(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            minimumSize: Size.zero,
            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
          ),
        ),
        const SizedBox(width: 8),
        
        // 复制按钮
        OutlinedButton.icon(
          onPressed: () => _copyTemplate(context, template),
          icon: const Icon(Icons.copy, size: 16),
          label: const Text('复制'),
          style: OutlinedButton.styleFrom(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            minimumSize: Size.zero,
            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
          ),
        ),
        const SizedBox(width: 8),
        
        // 测试按钮
        ElevatedButton.icon(
          onPressed: () => _testTemplate(context, template),
          icon: const Icon(Icons.send, size: 16),
          label: const Text('测试'),
          style: ElevatedButton.styleFrom(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            minimumSize: Size.zero,
            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
          ),
        ),
        
        const Spacer(),
        
        // 启用/禁用切换
        Switch(
          value: true, // TODO: 从设置中读取
          onChanged: (value) {
            // TODO: 更新模板启用状态
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('${template.displayName}已${value ? "启用" : "禁用"}')),
            );
          },
        ),
      ],
    );
  }

  /// 显示模板编辑器
  void _showTemplateEditor(
    BuildContext context,
    NotificationTemplateType template,
    WidgetRef ref,
  ) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _buildTemplateEditorSheet(context, template),
    );
  }

  /// 构建模板编辑器底部表单
  Widget _buildTemplateEditorSheet(BuildContext context, NotificationTemplateType template) {
    final templateController = TextEditingController(text: _getTemplatePreview(template));
    
    return DraggableScrollableSheet(
      initialChildSize: 0.8,
      minChildSize: 0.5,
      maxChildSize: 0.95,
      builder: (context, scrollController) {
        return Container(
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
          ),
          child: Column(
            children: [
              // 顶部栏
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.primaryContainer,
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
                ),
                child: Row(
                  children: [
                    Icon(Icons.edit, color: Theme.of(context).colorScheme.onPrimaryContainer),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        '编辑${template.displayName}模板',
                        style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                          color: Theme.of(context).colorScheme.onPrimaryContainer,
                        ),
                      ),
                    ),
                    IconButton(
                      onPressed: () => Navigator.of(context).pop(),
                      icon: Icon(
                        Icons.close,
                        color: Theme.of(context).colorScheme.onPrimaryContainer,
                      ),
                    ),
                  ],
                ),
              ),
              
              // 编辑区域
              Expanded(
                child: ListView(
                  controller: scrollController,
                  padding: const EdgeInsets.all(16),
                  children: [
                    // 模板编辑说明
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '变量说明',
                              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 8),
                            const Text('可用变量:'),
                            const SizedBox(height: 4),
                            Text(
                              '{condition_name} - 条件名称\n{result_value} - 结果值\n{result_details} - 结果详情\n{trigger_time} - 触发时间\n{symbol} - 交易对\n{priority} - 优先级\n{priority_emoji} - 优先级表情',
                              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                fontFamily: 'monospace',
                                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    
                    // 模板编辑器
                    TextField(
                      controller: templateController,
                      maxLines: 10,
                      decoration: InputDecoration(
                        labelText: '模板内容',
                        hintText: '输入通知模板内容...',
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        contentPadding: const EdgeInsets.all(16),
                      ),
                    ),
                    
                    const SizedBox(height: 16),
                    
                    // 预览区域
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '预览效果',
                              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Container(
                              width: double.infinity,
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: Theme.of(context).colorScheme.surfaceVariant.withOpacity(0.3),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Text(
                                templateController.text.isEmpty 
                                    ? '预览内容将显示在这里...'
                                    : templateController.text,
                                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                  fontFamily: 'monospace',
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              
              // 底部按钮
              Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () => Navigator.of(context).pop(),
                        child: const Text('取消'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: ElevatedButton(
                        onPressed: () {
                          // TODO: 保存模板
                          Navigator.of(context).pop();
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text('${template.displayName}模板已保存')),
                          );
                        },
                        child: const Text('保存'),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  /// 复制模板
  void _copyTemplate(BuildContext context, NotificationTemplateType template) {
    // TODO: 实现模板复制功能
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('${template.displayName}模板已复制')),
    );
  }

  /// 测试模板
  void _testTemplate(BuildContext context, NotificationTemplateType template) {
    // TODO: 实现模板测试功能
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('正在测试${template.displayName}模板...'),
        backgroundColor: Colors.blue,
      ),
    );
  }
}