import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

// 通知渠道类型
enum NotificationChannelType {
  popup('popup', '弹窗通知', Icons.web),
  desktop('desktop', '桌面通知', Icons.desktop_mac),
  telegram('telegram', 'Telegram', Icons.send),
  email('email', '邮件', Icons.email);

  const NotificationChannelType(this.value, this.displayName, this.icon);
  final String value;
  final String displayName;
  final IconData icon;
}

// 渠道状态
enum ChannelStatus {
  enabled('enabled', '已启用'),
  disabled('disabled', '已禁用'),
  error('error', '配置错误'),
  testing('testing', '测试中');

  const ChannelStatus(this.value, this.displayName);
  final String value;
  final String displayName;
}

// 通知模板类型
enum NotificationTemplateType {
  priceAlert('price_alert', '价格预警'),
  volumeAlert('volume_alert', '成交量预警'),
  technicalAlert('technical_alert', '技术指标预警'),
  emergencyAlert('emergency_alert', '紧急预警'),
  custom('custom', '自定义');

  const NotificationTemplateType(this.value, this.displayName);
  final String value;
  final String displayName;
}

// 通知渠道配置
class NotificationChannelConfig {
  final String id;
  final String name;
  final String description;
  final NotificationChannelType type;
  final bool enabled;
  final ChannelStatus status;
  final Map<String, dynamic> settings;
  final List<String> templateTypes;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? lastUsed;
  final Map<String, int> statistics;

  const NotificationChannelConfig({
    required this.id,
    required this.name,
    required this.description,
    required this.type,
    this.enabled = false,
    this.status = ChannelStatus.disabled,
    this.settings = const {},
    this.templateTypes = const [],
    required this.createdAt,
    required this.updatedAt,
    this.lastUsed,
    this.statistics = const {},
  });

  // 复制方法
  NotificationChannelConfig copyWith({
    String? id,
    String? name,
    String? description,
    NotificationChannelType? type,
    bool? enabled,
    ChannelStatus? status,
    Map<String, dynamic>? settings,
    List<String>? templateTypes,
    DateTime? createdAt,
    DateTime? updatedAt,
    DateTime? lastUsed,
    Map<String, int>? statistics,
  }) {
    return NotificationChannelConfig(
      id: id ?? this.id,
      name: name ?? this.name,
      description: description ?? this.description,
      type: type ?? this.type,
      enabled: enabled ?? this.enabled,
      status: status ?? this.status,
      settings: settings ?? this.settings,
      templateTypes: templateTypes ?? this.templateTypes,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      lastUsed: lastUsed ?? this.lastUsed,
      statistics: statistics ?? this.statistics,
    );
  }

  // JSON序列化
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'description': description,
      'type': type.value,
      'enabled': enabled,
      'status': status.value,
      'settings': settings,
      'templateTypes': templateTypes,
      'createdAt': createdAt.toIso8601String(),
      'updatedAt': updatedAt.toIso8601String(),
      'lastUsed': lastUsed?.toIso8601String(),
      'statistics': statistics,
    };
  }

  // JSON反序列化
  factory NotificationChannelConfig.fromJson(Map<String, dynamic> json) {
    return NotificationChannelConfig(
      id: json['id'],
      name: json['name'],
      description: json['description'],
      type: NotificationChannelType.values.firstWhere(
        (t) => t.value == json['type'],
      ),
      enabled: json['enabled'],
      status: ChannelStatus.values.firstWhere(
        (s) => s.value == json['status'],
      ),
      settings: Map<String, dynamic>.from(json['settings'] ?? {}),
      templateTypes: List<String>.from(json['templateTypes'] ?? []),
      createdAt: DateTime.parse(json['createdAt']),
      updatedAt: DateTime.parse(json['updatedAt']),
      lastUsed: json['lastUsed'] != null ? DateTime.parse(json['lastUsed']) : null,
      statistics: Map<String, int>.from(json['statistics'] ?? {}),
    );
  }

  // 获取状态显示颜色
  String get statusDisplay {
    return status.displayName;
  }

  // 获取类型显示
  String get typeDisplay {
    return type.displayName;
  }

  // 获取总发送次数
  int get totalSent {
    return statistics.values.fold(0, (sum, count) => sum + count);
  }

  // 获取成功率
  double get successRate {
    final total = totalSent;
    if (total == 0) return 0.0;
    final successful = statistics['successful'] ?? 0;
    return (successful / total) * 100;
  }
}

// 通知全局设置
class NotificationGlobalSettings {
  final bool enableNotifications;
  final bool enableSound;
  final bool enableVibration;
  final bool enableDesktopPopups;
  final Map<String, bool> templateEnabled;
  final Map<String, String> globalTemplateSettings;
  final int maxRetries;
  final int retryDelay;

  const NotificationGlobalSettings({
    this.enableNotifications = true,
    this.enableSound = true,
    this.enableVibration = true,
    this.enableDesktopPopups = true,
    this.templateEnabled = const {},
    this.globalTemplateSettings = const {},
    this.maxRetries = 3,
    this.retryDelay = 5000, // 毫秒
  });

  NotificationGlobalSettings copyWith({
    bool? enableNotifications,
    bool? enableSound,
    bool? enableVibration,
    bool? enableDesktopPopups,
    Map<String, bool>? templateEnabled,
    Map<String, String>? globalTemplateSettings,
    int? maxRetries,
    int? retryDelay,
  }) {
    return NotificationGlobalSettings(
      enableNotifications: enableNotifications ?? this.enableNotifications,
      enableSound: enableSound ?? this.enableSound,
      enableVibration: enableVibration ?? this.enableVibration,
      enableDesktopPopups: enableDesktopPopups ?? this.enableDesktopPopups,
      templateEnabled: templateEnabled ?? this.templateEnabled,
      globalTemplateSettings: globalTemplateSettings ?? this.globalTemplateSettings,
      maxRetries: maxRetries ?? this.maxRetries,
      retryDelay: retryDelay ?? this.retryDelay,
    );
  }
}

// Provider状态
class NotificationState {
  final List<NotificationChannelConfig> channels;
  final NotificationGlobalSettings globalSettings;
  final bool isLoading;
  final String? error;
  final Map<String, String> channelTests; // channel_id -> test_status

  const NotificationState({
    this.channels = const [],
    this.globalSettings = const NotificationGlobalSettings(),
    this.isLoading = false,
    this.error,
    this.channelTests = const {},
  });

  NotificationState copyWith({
    List<NotificationChannelConfig>? channels,
    NotificationGlobalSettings? globalSettings,
    bool? isLoading,
    String? error,
    Map<String, String>? channelTests,
  }) {
    return NotificationState(
      channels: channels ?? this.channels,
      globalSettings: globalSettings ?? this.globalSettings,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      channelTests: channelTests ?? this.channelTests,
    );
  }
}

// 通知管理Provider
class NotificationNotifier extends StateNotifier<NotificationState> {
  NotificationNotifier() : super(const NotificationState()) {
    _initializeChannels();
  }

  // 初始化渠道
  void _initializeChannels() {
    final now = DateTime.now();
    final defaultChannels = [
      NotificationChannelConfig(
        id: 'popup-1',
        name: '弹窗通知',
        description: '浏览器弹窗通知，适用于实时提醒',
        type: NotificationChannelType.popup,
        enabled: true,
        status: ChannelStatus.enabled,
        settings: {'timeout': 5000, 'priority': 'normal'},
        templateTypes: ['price_alert', 'volume_alert'],
        createdAt: now,
        updatedAt: now,
        statistics: {'total': 10, 'successful': 9, 'failed': 1},
      ),
      NotificationChannelConfig(
        id: 'desktop-1',
        name: '桌面通知',
        description: '系统桌面通知，支持所有桌面操作系统',
        type: NotificationChannelType.desktop,
        enabled: true,
        status: ChannelStatus.enabled,
        settings: {'timeout': 3000, 'urgency': 'normal'},
        templateTypes: ['price_alert', 'technical_alert', 'emergency_alert'],
        createdAt: now,
        updatedAt: now,
        statistics: {'total': 15, 'successful': 15, 'failed': 0},
      ),
      NotificationChannelConfig(
        id: 'telegram-1',
        name: 'Telegram通知',
        description: '通过Telegram Bot发送通知消息',
        type: NotificationChannelType.telegram,
        enabled: false,
        status: ChannelStatus.disabled,
        settings: {'bot_token': '', 'chat_id': ''},
        templateTypes: ['price_alert', 'volume_alert', 'technical_alert', 'emergency_alert'],
        createdAt: now,
        updatedAt: now,
        statistics: {'total': 0, 'successful': 0, 'failed': 0},
      ),
      NotificationChannelConfig(
        id: 'email-1',
        name: '邮件通知',
        description: '通过邮件发送详细通知',
        type: NotificationChannelType.email,
        enabled: false,
        status: ChannelStatus.disabled,
        settings: {'smtp_host': '', 'smtp_port': 587, 'username': '', 'password': ''},
        templateTypes: ['price_alert', 'volume_alert', 'technical_alert', 'emergency_alert'],
        createdAt: now,
        updatedAt: now,
        statistics: {'total': 0, 'successful': 0, 'failed': 0},
      ),
    ];

    state = state.copyWith(channels: defaultChannels);
  }

  // 切换渠道启用状态
  Future<void> toggleChannel(String channelId) async {
    state = state.copyWith(isLoading: true);
    try {
      await Future.delayed(const Duration(milliseconds: 300));
      
      final updatedChannels = state.channels.map((channel) {
        if (channel.id == channelId) {
          final newEnabled = !channel.enabled;
          final newStatus = newEnabled ? ChannelStatus.enabled : ChannelStatus.disabled;
          return channel.copyWith(
            enabled: newEnabled,
            status: newStatus,
            updatedAt: DateTime.now(),
          );
        }
        return channel;
      }).toList();

      state = state.copyWith(
        channels: updatedChannels,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  // 更新渠道配置
  Future<void> updateChannel(NotificationChannelConfig updatedChannel) async {
    state = state.copyWith(isLoading: true);
    try {
      await Future.delayed(const Duration(milliseconds: 300));
      
      final updatedChannels = state.channels.map((channel) {
        return channel.id == updatedChannel.id 
            ? updatedChannel.copyWith(updatedAt: DateTime.now())
            : channel;
      }).toList();

      state = state.copyWith(
        channels: updatedChannels,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  // 测试渠道连接
  Future<void> testChannel(String channelId) async {
    final channel = state.channels.firstWhere((c) => c.id == channelId);
    
    // 更新测试状态
    state = state.copyWith(
      channelTests: {...state.channelTests, channelId: 'testing'},
    );

    try {
      await Future.delayed(const Duration(seconds: 2));
      
      // 模拟测试结果
      final success = _simulateTestResult(channel);
      final newStatus = success ? ChannelStatus.enabled : ChannelStatus.error;
      
      // 更新渠道状态
      final updatedChannels = state.channels.map((c) {
        if (c.id == channelId) {
          return c.copyWith(
            status: newStatus,
            lastUsed: DateTime.now(),
            updatedAt: DateTime.now(),
          );
        }
        return c;
      }).toList();

      state = state.copyWith(
        channels: updatedChannels,
        channelTests: {...state.channelTests, channelId: success ? 'success' : 'error'},
      );
    } catch (e) {
      state = state.copyWith(
        channelTests: {...state.channelTests, channelId: 'error'},
      );
    }
  }

  // 模拟测试结果
  bool _simulateTestResult(NotificationChannelConfig channel) {
    switch (channel.type) {
      case NotificationChannelType.popup:
        return true; // 弹窗通知总是可用
      case NotificationChannelType.desktop:
        return true; // 桌面通知通常可用
      case NotificationChannelType.telegram:
        // 需要bot token和chat id
        return channel.settings['bot_token']?.isNotEmpty == true && 
               channel.settings['chat_id']?.isNotEmpty == true;
      case NotificationChannelType.email:
        // 需要SMTP配置
        return channel.settings['smtp_host']?.isNotEmpty == true && 
               channel.settings['username']?.isNotEmpty == true;
    }
  }

  // 更新全局设置
  Future<void> updateGlobalSettings(NotificationGlobalSettings newSettings) async {
    state = state.copyWith(isLoading: true);
    try {
      await Future.delayed(const Duration(milliseconds: 200));
      state = state.copyWith(
        globalSettings: newSettings,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  // 清除错误
  void clearError() {
    state = state.copyWith(error: null);
  }

  // 获取渠道统计
  Map<String, int> getChannelStatistics() {
    final stats = {
      'total_channels': state.channels.length,
      'enabled_channels': state.channels.where((c) => c.enabled).length,
      'disabled_channels': state.channels.where((c) => !c.enabled).length,
      'total_sent': state.channels.fold(0, (sum, c) => sum + c.totalSent),
      'total_successful': state.channels.fold(0, (sum, c) => sum + (c.statistics['successful'] ?? 0)),
      'total_failed': state.channels.fold(0, (sum, c) => sum + (c.statistics['failed'] ?? 0)),
    };

    return stats;
  }

  // 按类型分组渠道
  Map<NotificationChannelType, List<NotificationChannelConfig>> getChannelsByType() {
    final Map<NotificationChannelType, List<NotificationChannelConfig>> grouped = {};
    for (final channel in state.channels) {
      grouped.putIfAbsent(channel.type, () => []).add(channel);
    }
    return grouped;
  }

  // 获取可用模板类型
  List<NotificationTemplateType> getAvailableTemplates() {
    return NotificationTemplateType.values.toList();
  }

  // 批量测试所有渠道
  Future<void> testAllChannels() async {
    for (final channel in state.channels.where((c) => c.enabled)) {
      await testChannel(channel.id);
    }
  }
}

// Provider实例
final notificationProvider = StateNotifierProvider<NotificationNotifier, NotificationState>(
  (ref) => NotificationNotifier(),
);

// 渠道测试状态Provider
final channelTestStatusProvider = Provider<Map<String, String>>((ref) {
  final notificationState = ref.watch(notificationProvider);
  return notificationState.channelTests;
});

// 渠道统计Provider
final channelStatisticsProvider = Provider<Map<String, int>>((ref) {
  final notifier = ref.read(notificationProvider.notifier);
  return notifier.getChannelStatistics();
});

// 按类型分组的渠道Provider
final channelsByTypeProvider = Provider<Map<NotificationChannelType, List<NotificationChannelConfig>>>((ref) {
  final notificationState = ref.watch(notificationProvider);
  return notificationState.channels.fold<Map<NotificationChannelType, List<NotificationChannelConfig>>>({}, (grouped, channel) {
    grouped.putIfAbsent(channel.type, () => []).add(channel);
    return grouped;
  });
});
