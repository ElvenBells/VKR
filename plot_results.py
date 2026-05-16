#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генерация публикационных графиков: matplotlib + seaborn
Формат: векторный PDF, шрифт Times New Roman, ГОСТ-стиль
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path

# Настройка стиля для научных публикаций
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman'],
    'font.size': 11,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.titlesize': 14,
    'figure.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.format': 'pdf',  # Векторный формат для журнала
    'axes.grid': True,
    'grid.alpha': 0.3
})

def load_data():
    cv = pd.read_csv("results/cv_metrics.csv")
    dom = pd.read_csv("results/dom_metrics.csv")
    cv['approach'] = 'Hybrid CV'
    dom['approach'] = 'DOM Baseline'
    return pd.concat([cv, dom], ignore_index=True)

def plot_coverage_comparison(df):
    """Рис. 1: Сравнение Coverage по подходам и типам дефектов"""
    
    plt.figure(figsize=(8, 5))
    
    # Группировка данных
    plot_data = df.groupby(['approach', 'defect_type'])['coverage'].mean().reset_index()
    
    # Bar plot
    sns.barplot(data=plot_data, x='defect_type', y='coverage', hue='approach', 
                palette={'Hybrid CV': '#2563eb', 'DOM Baseline': '#64748b'},
                capsize=0.1, errorbar=('ci', 95))
    
    plt.xlabel('Тип дефекта')
    plt.ylabel('Defect Coverage (%)')
    plt.title('Сравнение полноты обнаружения визуальных дефектов')
    plt.xticks(rotation=45, ha='right')
    plt.legend(title='Подход', frameon=True)
    plt.ylim(0, 1.05)
    
    plt.tight_layout()
    plt.savefig("figures/fig1_coverage_comparison.pdf")
    plt.savefig("figures/fig1_coverage_comparison.png", dpi=300)
    plt.close()
    print("[✓] Рис. 1 сохранён: figures/fig1_coverage_comparison.pdf")

def plot_fpr_time_scatter(df):
    """Рис. 2: Scatter FPR vs Execution Time"""
    
    plt.figure(figsize=(7, 5))
    
    # Агрегация по запускам
    agg = df.groupby(['approach', 'site', 'defect_type']).agg({
        'fpr': 'mean',
        'exec_time_ms': 'mean'
    }).reset_index()
    
    # Scatter с размерами по FNR
    for approach, color in [('Hybrid CV', '#2563eb'), ('DOM Baseline', '#64748b')]:
        subset = agg[agg['approach'] == approach]
        plt.scatter(subset['fpr'], subset['exec_time_ms'], 
                   c=color, label=approach, alpha=0.7, s=60, edgecolors='white')
    
    plt.xlabel('False Positive Rate (FPR)')
    plt.ylabel('Execution Time (ms)')
    plt.title('Точность vs Производительность')
    plt.legend(frameon=True)
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig("figures/fig2_fpr_vs_time.pdf")
    plt.savefig("figures/fig2_fpr_vs_time.png", dpi=300)
    plt.close()
    print("[✓] Рис. 2 сохранён: figures/fig2_fpr_vs_time.pdf")

def plot_ssim_distribution(df):
    """Рис. 3: Распределение SSIM по типам дефектов (если есть данные)"""
    
    try:
        ssim_df = pd.read_csv("results/defect_metrics.csv")
        
        plt.figure(figsize=(8, 4))
        
        sns.boxplot(data=ssim_df, x='defect_type', y='ssim_score', 
                   palette='Set2', linewidth=1.5)
        
        plt.xlabel('Тип инжекции дефекта')
        plt.ylabel('SSIM Score (структурное сходство)')
        plt.title('Чувствительность визуальной регрессии к типам дефектов')
        plt.xticks(rotation=45, ha='right')
        plt.ylim(0.7, 1.0)
        plt.axhline(y=0.95, color='red', linestyle='--', linewidth=0.8, label='Порог детекции')
        plt.legend(frameon=True, fontsize=9)
        
        plt.tight_layout()
        plt.savefig("figures/fig3_ssim_distribution.pdf")
        plt.savefig("figures/fig3_ssim_distribution.png", dpi=300)
        plt.close()
        print("[✓] Рис. 3 сохранён: figures/fig3_ssim_distribution.pdf")
        
    except FileNotFoundError:
        print("[⚠] Файл defect_metrics.csv не найден, пропускаем Рис. 3")

def main():
    print("="*70)
    print("ГЕНЕРАЦИЯ ГРАФИКОВ ДЛЯ СТАТЬИ")
    print("="*70)
    
    Path("figures").mkdir(exist_ok=True)
    
    df = load_data()
    print(f"[✓] Загружено {len(df)} записей для визуализации")
    
    plot_coverage_comparison(df)
    plot_fpr_time_scatter(df)
    plot_ssim_distribution(df)
    
    print("\n[✅] Все графики сохранены в папке 'figures/'")
    print("Формат: PDF (вектор) + PNG (растр, 300 DPI)")
    print("Шрифт: Times New Roman, размер 10–12 pt")

if __name__ == "__main__":
    main()