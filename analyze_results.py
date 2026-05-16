#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализ результатов эксперимента: агрегация, статистика, экспорт таблиц
"""

import pandas as pd
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

def load_and_aggregate():
    """Загрузка и агрегация данных из CSV"""
    
    # Загружаем данные
    cv = pd.read_csv("results/cv_metrics.csv")
    dom = pd.read_csv("results/dom_metrics.csv")
    
    # Объединяем с маркером подхода
    cv['approach'] = 'Hybrid_CV'
    dom['approach'] = 'DOM_Baseline'
    merged = pd.concat([cv, dom], ignore_index=True)
    
    print(f"[✓] Загружено записей: CV={len(cv)}, DOM={len(dom)}, Total={len(merged)}")
    return merged

def calculate_summary(merged):
    """Расчёт сводных метрик по подходам"""
    
    summary = merged.groupby(['approach', 'defect_type']).agg({
        'coverage': ['mean', 'std', 'min', 'max'],
        'fpr': ['mean', 'std'],
        'fnr': ['mean', 'std'],
        'exec_time_ms': ['mean', 'std', 'median'],
        'precision': ['mean', 'std']
    }).round(4)
    
    return summary

def statistical_test(merged):
    """Проверка статистической значимости различий (t-test / Wilcoxon)"""
    
    print("\n" + "="*70)
    print("СТАТИСТИЧЕСКАЯ ПРОВЕРКА ЗНАЧИМОСТИ (α=0.05)")
    print("="*70)
    
    results = []
    
    for metric in ['coverage', 'fpr', 'fnr', 'exec_time_ms']:
        cv_vals = merged[merged['approach'] == 'Hybrid_CV'][metric].dropna()
        dom_vals = merged[merged['approach'] == 'DOM_Baseline'][metric].dropna()
        
        if len(cv_vals) < 2 or len(dom_vals) < 2:
            continue
            
        # Проверка нормальности распределения (Shapiro-Wilk)
        _, cv_norm = stats.shapiro(cv_vals)
        _, dom_norm = stats.shapiro(dom_vals)
        
        # Выбор теста: t-test если нормальное, иначе Wilcoxon
        if cv_norm > 0.05 and dom_norm > 0.05:
            t_stat, p_val = stats.ttest_ind(cv_vals, dom_vals, equal_var=False)
            test_name = "t-test (Welch)"
        else:
            t_stat, p_val = stats.mannwhitneyu(cv_vals, dom_vals, alternative='two-sided')
            test_name = "Mann-Whitney U"
        
        significant = p_val < 0.05
        cv_mean = cv_vals.mean()
        dom_mean = dom_vals.mean()
        improvement = ((cv_mean - dom_mean) / dom_mean * 100) if metric != 'fpr' and metric != 'fnr' else ((dom_mean - cv_mean) / dom_mean * 100)
        
        results.append({
            'metric': metric,
            'cv_mean': round(cv_mean, 4),
            'dom_mean': round(dom_mean, 4),
            'improvement_%': round(improvement, 2),
            'p_value': round(p_val, 5),
            'significant': significant,
            'test_used': test_name
        })
        
        status = "✓ ЗНАЧИМО" if significant else "✗ НЕ значимо"
        direction = "↑" if metric in ['coverage', 'precision'] else "↓"
        print(f"{metric:15} | CV: {cv_mean:.4f} | DOM: {dom_mean:.4f} | {direction} {improvement:+.2f}% | p={p_val:.5f} [{test_name}] {status}")
    
    return pd.DataFrame(results)

def export_tables(merged, summary, stats_df):
    """Экспорт таблиц в формате для статьи"""
    
    # Таблица 1: Сводные метрики по подходам (для вставки в статью)
    table1 = merged.groupby('approach').agg({
        'coverage': lambda x: f"{x.mean():.3f} ± {x.std():.3f}",
        'fpr': lambda x: f"{x.mean():.3f} ± {x.std():.3f}",
        'fnr': lambda x: f"{x.mean():.3f} ± {x.std():.3f}",
        'exec_time_ms': lambda x: f"{x.mean():.1f} ± {x.std():.1f}",
        'precision': lambda x: f"{x.mean():.3f} ± {x.std():.3f}"
    }).T.reset_index()
    table1.columns = ['Metric', 'Hybrid_CV', 'DOM_Baseline']
    table1.to_csv("results/table1_for_article.csv", index=False)
    print("\n[✓] Таблица 1 (сводные метрики) экспортирована: results/table1_for_article.csv")
    
    # Таблица 2: Результаты по типам дефектов
    table2 = merged.groupby(['approach', 'defect_type'])['coverage'].agg(['mean', 'std']).round(3)
    table2.to_csv("results/table2_coverage_by_defect.csv")
    print("[✓] Таблица 2 (покрытие по дефектам) экспортирована: results/table2_coverage_by_defect.csv")
    
    # Таблица 3: Статистическая значимость
    stats_df.to_csv("results/table3_statistical_significance.csv", index=False)
    print("[✓] Таблица 3 (статистика) экспортирована: results/table3_statistical_significance.csv")
    
    return table1, table2, stats_df

def main():
    print("="*70)
    print("АНАЛИЗ РЕЗУЛЬТАТОВ ЭКСПЕРИМЕНТА")
    print("="*70)
    
    # 1. Загрузка данных
    merged = load_and_aggregate()
    
    # 2. Сводная статистика
    summary = calculate_summary(merged)
    print("\n[✓] Сводная статистика рассчитана")
    
    # 3. Статистическая проверка
    stats_df = statistical_test(merged)
    
    # 4. Экспорт таблиц
    export_tables(merged, summary, stats_df)
    
    # 5. Быстрый инсайт для статьи
    print("\n" + "="*70)
    print("КЛЮЧЕВЫЕ ИНСАЙТЫ ДЛЯ РАЗДЕЛА 'РЕЗУЛЬТАТЫ'")
    print("="*70)
    
    cv_cov = merged[merged['approach'] == 'Hybrid_CV']['coverage'].mean()
    dom_cov = merged[merged['approach'] == 'DOM_Baseline']['coverage'].mean()
    cv_fpr = merged[merged['approach'] == 'Hybrid_CV']['fpr'].mean()
    dom_fpr = merged[merged['approach'] == 'DOM_Baseline']['fpr'].mean()
    
    print(f"• Покрытие дефектов: гибридный подход {cv_cov:.1%} vs DOM-базлайн {dom_cov:.1%} (Δ = {(cv_cov-dom_cov)*100:+.1f} п.п.)")
    print(f"• Ложные срабатывания: гибридный подход {cv_fpr:.1%} vs DOM-базлайн {dom_fpr:.1%} (Δ = {(cv_fpr-dom_fpr)*100:+.1f} п.п.)")
    print(f"• Статистическая значимость: {'подтверждена (p<0.05)' if (stats_df['significant'].any()) else 'требует дополнительных данных'}")

if __name__ == "__main__":
    main()