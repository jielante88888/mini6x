import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Material 3 Design System for Windows Desktop Trading Terminal
/// 
/// Provides comprehensive theming with dark/light modes optimized for
/// professional trading applications with enhanced accessibility features.
class AppTheme {
  // =============================================================================
  // DESIGN TOKENS - Color System
  // =============================================================================
  
  // Primary Brand Colors (Trading Professional Theme)
  static const Color primaryBlue = Color(0xFF1976D2);
  static const Color primaryBlueLight = Color(0xFF42A5F5);
  static const Color primaryBlueDark = Color(0xFF1565C0);
  
  // Accent Colors (Trading-specific semantics)
  static const Color accentGreen = Color(0xFF4CAF50);
  static const Color accentRed = Color(0xFFF44336);
  static const Color accentOrange = Color(0xFFFF9800);
  static const Color accentPurple = Color(0xFF9C27B0);
  static const Color accentTeal = Color(0xFF009688);
  
  // Semantic Colors (Market Data & Status)
  static const Color profitGreen = Color(0xFF4CAF50);
  static const Color lossRed = Color(0xFFF44336);
  static const Color neutralGray = Color(0xFF9E9E9E);
  static const Color warningYellow = Color(0xFFFFC107);
  static const Color infoBlue = Color(0xFF2196F3);
  
  // Surface Colors (Material 3 Surface System)
  static const Color surfaceBright = Color(0xFFFEFBFF);
  static const Color surfaceDim = Color(0xFF1C1B1F);
  static const Color surfaceContainerLowest = Color(0xFF000000);
  static const Color surfaceContainerLow = Color(0xFFE7E0EC);
  static const Color surfaceContainer = Color(0xFFF5F5F5);
  static const Color surfaceContainerHigh = Color(0xFFEEEEEE);
  static const Color surfaceContainerHighest = Color(0xFFDED8E1);
  
  // Background Colors
  static const Color backgroundPrimary = Color(0xFFFEFBFF);
  static const Color backgroundSecondary = Color(0xFF1C1B1F);
  static const Color backgroundTrading = Color(0xFF121212);
  
  // Text Colors (High Contrast for Trading)
  static const Color textPrimary = Color(0xFF1C1B1F);
  static const Color textSecondary = Color(0xFF49454F);
  static const Color textTertiary = Color(0xFF79747E);
  static const Color textDisabled = Color(0xFFCAC4D0);
  static const Color textInverse = Color(0xFFFFFFFF);
  
  // Interactive Colors
  static const Color interactivePrimary = Color(0xFF6750A4);
  static const Color interactivePrimaryContainer = Color(0xFFEADDFF);
  static const Color interactiveSecondary = Color(0xFF625B71);
  static const Color interactiveSecondaryContainer = Color(0xFFE8DEF8);
  
  // =============================================================================
  // DARK THEME - Material 3 Optimized for Trading
  // =============================================================================
  
  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      
      // Core Color Scheme
      colorScheme: const ColorScheme.dark(
        primary: primaryBlue,
        onPrimary: textInverse,
        primaryContainer: primaryBlueDark,
        onPrimaryContainer: textInverse,
        secondary: accentGreen,
        onSecondary: textInverse,
        secondaryContainer: Color(0xFF1B5E20),
        onSecondaryContainer: Color(0xFF4CAF50),
        tertiary: accentOrange,
        onTertiary: textInverse,
        tertiaryContainer: Color(0xFFE65100),
        onTertiaryContainer: Color(0xFFFF9800),
        
        // Surfaces
        surface: backgroundTrading,
        onSurface: textInverse,
        surfaceVariant: Color(0xFF2C2C2C),
        onSurfaceVariant: Color(0xFFCCCCCC),
        surfaceTint: primaryBlue,
        inverseSurface: Color(0xFFEEEEEE),
        onInverseSurface: textPrimary,
        inversePrimary: primaryBlueDark,
        
        // Backgrounds
        background: backgroundTrading,
        onBackground: textInverse,
        
        // Interactive States
        error: lossRed,
        onError: textInverse,
        errorContainer: Color(0xFF8B0000),
        onErrorContainer: Color(0xFFFFCDD2),
        
        outline: Color(0xFF938F99),
        outlineVariant: Color(0xFF49454F),
        shadow: Color(0xFF000000),
        scrim: Color(0xFF000000),
      ),
      
      // =============================================================================
      // APP BAR THEME
      // =============================================================================
      
      appBarTheme: const AppBarTheme(
        backgroundColor: Color(0xFF1E1E1E),
        foregroundColor: textInverse,
        elevation: 0,
        centerTitle: true,
        scrolledUnderElevation: 1,
        shadowColor: Color(0xFF000000),
        surfaceTintColor: Colors.transparent,
        titleTextStyle: TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.w600,
          color: textInverse,
          letterSpacing: 0.1,
        ),
      ),
      
      // =============================================================================
      // CARD THEME (Enhanced for Data Display)
      // =============================================================================
      
      cardTheme: CardTheme(
        color: const Color(0xFF252525),
        elevation: 2,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: Color(0xFF404040), width: 0.5),
        ),
        margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      ),
      
      // =============================================================================
      // ICON THEME
      // =============================================================================
      
      iconTheme: const IconThemeData(
        color: Color(0xFFCCCCCC),
        size: 24,
      ),
      
      // =============================================================================
      // BUTTON THEMES (Trading Actions)
      // =============================================================================
      
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primaryBlue,
          foregroundColor: textInverse,
          elevation: 2,
          shadowColor: const Color(0xFF000000),
          surfaceTintColor: Colors.transparent,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          textStyle: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.1,
          ),
        ).copyWith(
          backgroundColor: MaterialStateProperty.resolveWith<Color>((states) {
            if (states.contains(MaterialState.disabled)) {
              return const Color(0xFF404040);
            }
            if (states.contains(MaterialState.pressed)) {
              return primaryBlueDark;
            }
            if (states.contains(MaterialState.hovered)) {
              return primaryBlueLight;
            }
            return primaryBlue;
          }),
        ),
      ),
      
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: const Color(0xFF404040),
          foregroundColor: textInverse,
          elevation: 0,
          surfaceTintColor: Colors.transparent,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          textStyle: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.1,
          ),
        ),
      ),
      
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: primaryBlue,
          side: const BorderSide(color: Color(0xFF404040)),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          textStyle: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.1,
          ),
        ),
      ),
      
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: primaryBlue,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          textStyle: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.1,
          ),
        ),
      ),
      
      // =============================================================================
      // FLOATING ACTION BUTTON THEME
      // =============================================================================
      
      floatingActionButtonTheme: const FloatingActionButtonThemeData(
        backgroundColor: primaryBlue,
        foregroundColor: textInverse,
        elevation: 6,
        focusElevation: 8,
        hoverElevation: 8,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(16)),
        ),
      ),
      
      // =============================================================================
      // TEXT FIELD THEMES (Enhanced for Data Entry)
      // =============================================================================
      
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0xFF2D2D2D),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0xFF404040), width: 1),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: primaryBlue, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: lossRed, width: 1),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: lossRed, width: 2),
        ),
        labelStyle: const TextStyle(
          color: Color(0xFFCCCCCC),
          fontSize: 16,
        ),
        hintStyle: const TextStyle(
          color: Color(0xFF999999),
          fontSize: 16,
        ),
        errorStyle: const TextStyle(
          color: lossRed,
          fontSize: 14,
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      ),
      
      // =============================================================================
      // TYPOGRAPHY SYSTEM (Enhanced for Trading Data)
      // =============================================================================
      
      textTheme: const TextTheme(
        displayLarge: TextStyle(
          fontSize: 57,
          fontWeight: FontWeight.w400,
          letterSpacing: -0.25,
          color: textInverse,
          height: 1.12,
        ),
        displayMedium: TextStyle(
          fontSize: 45,
          fontWeight: FontWeight.w400,
          letterSpacing: 0,
          color: textInverse,
          height: 1.16,
        ),
        displaySmall: TextStyle(
          fontSize: 36,
          fontWeight: FontWeight.w400,
          letterSpacing: 0,
          color: textInverse,
          height: 1.22,
        ),
        headlineLarge: TextStyle(
          fontSize: 32,
          fontWeight: FontWeight.w600,
          letterSpacing: 0,
          color: textInverse,
          height: 1.25,
        ),
        headlineMedium: TextStyle(
          fontSize: 28,
          fontWeight: FontWeight.w600,
          letterSpacing: 0,
          color: textInverse,
          height: 1.29,
        ),
        headlineSmall: TextStyle(
          fontSize: 24,
          fontWeight: FontWeight.w600,
          letterSpacing: 0,
          color: textInverse,
          height: 1.33,
        ),
        titleLarge: TextStyle(
          fontSize: 22,
          fontWeight: FontWeight.w600,
          letterSpacing: 0,
          color: textInverse,
          height: 1.27,
        ),
        titleMedium: TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.15,
          color: textInverse,
          height: 1.5,
        ),
        titleSmall: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.1,
          color: Color(0xFFCCCCCC),
          height: 1.43,
        ),
        bodyLarge: TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w400,
          letterSpacing: 0.5,
          color: Color(0xFFCCCCCC),
          height: 1.5,
        ),
        bodyMedium: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w400,
          letterSpacing: 0.25,
          color: Color(0xFFCCCCCC),
          height: 1.43,
        ),
        bodySmall: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w400,
          letterSpacing: 0.4,
          color: Color(0xFF999999),
          height: 1.33,
        ),
        labelLarge: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.1,
          color: Color(0xFFCCCCCC),
          height: 1.43,
        ),
        labelMedium: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.5,
          color: Color(0xFFCCCCCC),
          height: 1.33,
        ),
        labelSmall: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.5,
          color: Color(0xFF999999),
          height: 1.45,
        ),
      ),
      
      // =============================================================================
      // NAVIGATION THEME (Desktop Optimized)
      // =============================================================================
      
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: const Color(0xFF1E1E1E),
        surfaceTintColor: Colors.transparent,
        indicatorColor: const Color(0xFF404040),
        labelTextStyle: const WidgetStateProperty<TextStyle>(
          TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.1,
          ),
        ),
      ),
      
      navigationRailTheme: NavigationRailThemeData(
        backgroundColor: const Color(0xFF1E1E1E),
        surfaceTintColor: Colors.transparent,
        indicatorColor: const Color(0xFF404040),
        selectedLabelTextStyle: const TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
        unselectedLabelTextStyle: const TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w500,
        ),
      ),
      
      // =============================================================================
      // DRAWER THEME
      // =============================================================================
      
      drawerTheme: const DrawerTheme(
        backgroundColor: Color(0xFF1E1E1E),
        surfaceTintColor: Colors.transparent,
      ),
      
      // =============================================================================
      // LIST TILE THEME (Enhanced for Data Lists)
      // =============================================================================
      
      listTileTheme: const ListTileThemeData(
        contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        titleTextStyle: TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w500,
          color: textInverse,
        ),
        subtitleTextStyle: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w400,
          color: Color(0xFFCCCCCC),
        ),
        leadingAndTrailingTextStyle: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w500,
          color: Color(0xFFCCCCCC),
        ),
      ),
      
      // =============================================================================
      // DIVIDER THEME
      // =============================================================================
      
      dividerTheme: const DividerThemeData(
        color: Color(0xFF404040),
        thickness: 1,
        space: 1,
      ),
      
      // =============================================================================
      // CHIPS THEME (For Filters & Tags)
      // =============================================================================
      
      chipTheme: ChipThemeData(
        backgroundColor: const Color(0xFF2D2D2D),
        selectedColor: primaryBlue.withOpacity(0.3),
        disabledColor: const Color(0xFF404040),
        labelStyle: const TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w500,
          color: Color(0xFFCCCCCC),
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
          side: const BorderSide(color: Color(0xFF404040)),
        ),
      ),
      
      // =============================================================================
      // PROGRESS INDICATOR THEME
      // =============================================================================
      
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: primaryBlue,
        linearTrackColor: Color(0xFF404040),
        circularTrackColor: Color(0xFF404040),
      ),
      
      // =============================================================================
      // SNACKBAR THEME
      // =============================================================================
      
      snackBarTheme: SnackBarThemeData(
        backgroundColor: const Color(0xFF323232),
        actionTextColor: primaryBlue,
        contentTextStyle: const TextStyle(
          color: textInverse,
          fontSize: 14,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
        behavior: SnackBarBehavior.floating,
        margin: const EdgeInsets.all(16),
      ),
      
      // =============================================================================
      // TOOLTIP THEME
      // =============================================================================
      
      tooltipTheme: const TooltipThemeData(
        backgroundColor: Color(0xFF323232),
        textStyle: TextStyle(
          color: textInverse,
          fontSize: 14,
          fontWeight: FontWeight.w500,
        ),
        decoration: BoxDecoration(
          color: Color(0xFF323232),
          borderRadius: BorderRadius.all(Radius.circular(8)),
        ),
      ),
      
      // =============================================================================
      // DIALOG THEME
      // =============================================================================
      
      dialogTheme: DialogTheme(
        backgroundColor: const Color(0xFF2D2D2D),
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: Color(0xFF404040)),
        ),
        titleTextStyle: const TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.w600,
          color: textInverse,
        ),
        contentTextStyle: const TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w400,
          color: Color(0xFFCCCCCC),
        ),
      ),
      
      // =============================================================================
      // ANIMATION & MOTION
      // =============================================================================
      
      splashColor: primaryBlue.withOpacity(0.3),
      highlightColor: primaryBlue.withOpacity(0.2),
      
      // =============================================================================
      // ACCESSIBILITY ENHANCEMENTS
      // =============================================================================
      
      visualDensity: VisualDensity.adaptivePlatformDensity,
      
      // =============================================================================
      // WINDOWS DESKTOP OPTIMIZATIONS
      // =============================================================================
      
      platform: TargetPlatform.windows,
      
      // =============================================================================
      // FONT CONFIGURATION
      // =============================================================================
      
      fontFamily: 'Segoe UI',
      
    );
  }
  
  // =============================================================================
  // LIGHT THEME - Professional Light Mode
  // =============================================================================
  
  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      
      // Core Color Scheme
      colorScheme: const ColorScheme.light(
        primary: primaryBlue,
        onPrimary: textInverse,
        primaryContainer: Color(0xFFBBDEFB),
        onPrimaryContainer: Color(0xFF1565C0),
        secondary: accentGreen,
        onSecondary: textInverse,
        secondaryContainer: Color(0xFFC8E6C9),
        onSecondaryContainer: Color(0xFF1B5E20),
        tertiary: accentOrange,
        onTertiary: textInverse,
        tertiaryContainer: Color(0xFFFFE0B2),
        onTertiaryContainer: Color(0xFFE65100),
        
        // Surfaces
        surface: Colors.white,
        onSurface: textPrimary,
        surfaceVariant: Color(0xFFF5F5F5),
        onSurfaceVariant: textSecondary,
        surfaceTint: primaryBlue,
        inverseSurface: Color(0xFF313033),
        onInverseSurface: textInverse,
        inversePrimary: Color(0xFFBBDEFB),
        
        // Backgrounds
        background: backgroundPrimary,
        onBackground: textPrimary,
        
        // Interactive States
        error: lossRed,
        onError: textInverse,
        errorContainer: Color(0xFFFFCDD2),
        onErrorContainer: Color(0xFF8B0000),
        
        outline: textTertiary,
        outlineVariant: Color(0xFFCAC4D0),
        shadow: Color(0xFF000000),
        scrim: Color(0xFF000000),
      ),
      
      // Enhanced component themes for light mode
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.white,
        foregroundColor: textPrimary,
        elevation: 0,
        centerTitle: true,
        scrolledUnderElevation: 1,
        shadowColor: Color(0xFF000000),
        surfaceTintColor: Colors.transparent,
        titleTextStyle: TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.w600,
          color: textPrimary,
          letterSpacing: 0.1,
        ),
      ),
      
      cardTheme: CardTheme(
        color: Colors.white,
        elevation: 2,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: Color(0xFFE0E0E0), width: 0.5),
        ),
        margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      ),
      
      // Enhanced text theme for light mode
      textTheme: const TextTheme(
        displayLarge: TextStyle(
          fontSize: 57,
          fontWeight: FontWeight.w400,
          letterSpacing: -0.25,
          color: textPrimary,
          height: 1.12,
        ),
        displayMedium: TextStyle(
          fontSize: 45,
          fontWeight: FontWeight.w400,
          letterSpacing: 0,
          color: textPrimary,
          height: 1.16,
        ),
        displaySmall: TextStyle(
          fontSize: 36,
          fontWeight: FontWeight.w400,
          letterSpacing: 0,
          color: textPrimary,
          height: 1.22,
        ),
        headlineLarge: TextStyle(
          fontSize: 32,
          fontWeight: FontWeight.w600,
          letterSpacing: 0,
          color: textPrimary,
          height: 1.25,
        ),
        headlineMedium: TextStyle(
          fontSize: 28,
          fontWeight: FontWeight.w600,
          letterSpacing: 0,
          color: textPrimary,
          height: 1.29,
        ),
        headlineSmall: TextStyle(
          fontSize: 24,
          fontWeight: FontWeight.w600,
          letterSpacing: 0,
          color: textPrimary,
          height: 1.33,
        ),
        titleLarge: TextStyle(
          fontSize: 22,
          fontWeight: FontWeight.w600,
          letterSpacing: 0,
          color: textPrimary,
          height: 1.27,
        ),
        titleMedium: TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.15,
          color: textPrimary,
          height: 1.5,
        ),
        titleSmall: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.1,
          color: textSecondary,
          height: 1.43,
        ),
        bodyLarge: TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w400,
          letterSpacing: 0.5,
          color: textPrimary,
          height: 1.5,
        ),
        bodyMedium: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w400,
          letterSpacing: 0.25,
          color: textSecondary,
          height: 1.43,
        ),
        bodySmall: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w400,
          letterSpacing: 0.4,
          color: textTertiary,
          height: 1.33,
        ),
        labelLarge: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.1,
          color: textSecondary,
          height: 1.43,
        ),
        labelMedium: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.5,
          color: textSecondary,
          height: 1.33,
        ),
        labelSmall: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.5,
          color: textTertiary,
          height: 1.45,
        ),
      ),
      
      // Enhanced input decoration for light mode
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0xFFF5F5F5),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0xFFE0E0E0), width: 1),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: primaryBlue, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: lossRed, width: 1),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: lossRed, width: 2),
        ),
        labelStyle: const TextStyle(
          color: textSecondary,
          fontSize: 16,
        ),
        hintStyle: const TextStyle(
          color: textTertiary,
          fontSize: 16,
        ),
        errorStyle: const TextStyle(
          color: lossRed,
          fontSize: 14,
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      ),
      
      // Enhanced navigation themes for light mode
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: Colors.white,
        surfaceTintColor: Colors.transparent,
        indicatorColor: const Color(0xFFE3F2FD),
        labelTextStyle: const WidgetStateProperty<TextStyle>(
          TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.1,
          ),
        ),
      ),
      
      // Accessibility and platform optimizations
      visualDensity: VisualDensity.adaptivePlatformDensity,
      platform: TargetPlatform.windows,
      fontFamily: 'Segoe UI',
    );
  }
  
  // =============================================================================
  // UTILITY METHODS
  // =============================================================================
  
  /// Get trading-specific color based on value
  static Color getTradingColor(double value, {bool isPercentage = false}) {
    if (value > 0) {
      return profitGreen;
    } else if (value < 0) {
      return lossRed;
    } else {
      return neutralGray;
    }
  }
  
  /// Get semantic color for trading actions
  static Color getActionColor(String action) {
    switch (action.toLowerCase()) {
      case 'buy':
      case 'long':
      case 'bullish':
        return profitGreen;
      case 'sell':
      case 'short':
      case 'bearish':
        return lossRed;
      case 'hold':
      case 'neutral':
        return neutralGray;
      case 'warning':
      case 'alert':
        return warningYellow;
      case 'info':
      case 'notification':
        return infoBlue;
      default:
        return primaryBlue;
    }
  }
  
  /// Get high contrast text color for given background
  static Color getContrastColor(Color background) {
    // Calculate luminance to determine contrast
    final luminance = background.computeLuminance();
    return luminance > 0.5 ? textPrimary : textInverse;
  }
  
  /// Get theme brightness
  static Brightness getThemeBrightness(ThemeData theme) {
    return theme.brightness;
  }
  
  /// Check if current theme is dark
  static bool isDarkTheme(ThemeData theme) {
    return theme.brightness == Brightness.dark;
  }
  
  /// Get dynamic status bar style
  static SystemUiOverlayStyle getStatusBarStyle(ThemeData theme) {
    return isDarkTheme(theme) 
        ? SystemUiOverlayStyle.light
        : SystemUiOverlayStyle.dark;
  }
}