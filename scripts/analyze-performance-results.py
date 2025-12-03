#!/usr/bin/env python3
"""
Performance Test Results Analyzer
Creates comprehensive analysis and visualizations for leadership
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import style
import pandas as pd
import numpy as np

# Use a professional style
style.use('seaborn-v0_8-darkgrid')
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 10

def load_results(json_file):
    """Load performance test results from JSON file"""
    with open(json_file, 'r') as f:
        return json.load(f)

def create_summary_stats(results):
    """Create summary statistics"""
    summary = {
        'total_users': results.get('total_users', 0),
        'total_queries': results.get('total_queries', 0),
        'successful_queries': results.get('successful_queries', 0),
        'failed_queries': results.get('failed_queries', 0),
        'avg_response_time': results.get('avg_response_time', 0),
        'p95_response_time': results.get('p95_response_time', 0),
        'p99_response_time': results.get('p99_response_time', 0),
        'avg_first_chunk_time': results.get('avg_first_chunk_time', 0),
        'throughput': results.get('throughput', 0),
        'error_rate': results.get('error_rate', 0),
        'avg_response_length': results.get('avg_response_length', 0),
        'avg_quality_score': results.get('avg_quality_score', 0),
        'test_duration': results.get('test_duration', 0),
    }
    return summary

def create_visualizations(results, output_dir):
    """Create comprehensive visualizations"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract data
    queries = results.get('queries', [])
    if not queries:
        print("⚠️  No query data found in results")
        return
    
    df = pd.DataFrame(queries)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
    
    # 1. Response Time Distribution
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Performance Test Results - Response Time Analysis', fontsize=16, fontweight='bold')
    
    # Response time over time
    ax1 = axes[0, 0]
    ax1.plot(df['timestamp'], df['response_time'], alpha=0.6, linewidth=0.5, color='#2E86AB')
    ax1.axhline(y=df['response_time'].mean(), color='r', linestyle='--', label=f'Mean: {df["response_time"].mean():.2f}s')
    ax1.axhline(y=df['response_time'].quantile(0.95), color='orange', linestyle='--', label=f'P95: {df["response_time"].quantile(0.95):.2f}s')
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Response Time (seconds)')
    ax1.set_title('Response Time Over Time')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    
    # Response time histogram
    ax2 = axes[0, 1]
    ax2.hist(df['response_time'], bins=50, color='#A23B72', edgecolor='black', alpha=0.7)
    ax2.axvline(x=df['response_time'].mean(), color='r', linestyle='--', linewidth=2, label=f'Mean: {df["response_time"].mean():.2f}s')
    ax2.axvline(x=df['response_time'].quantile(0.95), color='orange', linestyle='--', linewidth=2, label=f'P95: {df["response_time"].quantile(0.95):.2f}s')
    ax2.set_xlabel('Response Time (seconds)')
    ax2.set_ylabel('Frequency')
    ax2.set_title('Response Time Distribution')
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='y')
    
    # First chunk time over time
    ax3 = axes[1, 0]
    if 'first_chunk_time' in df.columns:
        ax3.plot(df['timestamp'], df['first_chunk_time'], alpha=0.6, linewidth=0.5, color='#F18F01')
        ax3.axhline(y=df['first_chunk_time'].mean(), color='r', linestyle='--', label=f'Mean: {df["first_chunk_time"].mean():.2f}s')
        ax3.set_xlabel('Time')
        ax3.set_ylabel('First Chunk Time (seconds)')
        ax3.set_title('Time to First Chunk (TTFB)')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)
    
    # Response time percentiles
    ax4 = axes[1, 1]
    percentiles = [50, 75, 90, 95, 99]
    values = [df['response_time'].quantile(p/100) for p in percentiles]
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E']
    bars = ax4.bar(range(len(percentiles)), values, color=colors, edgecolor='black', alpha=0.7)
    ax4.set_xticks(range(len(percentiles)))
    ax4.set_xticklabels([f'P{p}' for p in percentiles])
    ax4.set_ylabel('Response Time (seconds)')
    ax4.set_title('Response Time Percentiles')
    ax4.grid(True, alpha=0.3, axis='y')
    # Add value labels on bars
    for i, (bar, val) in enumerate(zip(bars, values)):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.2f}s', ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'response_time_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. Throughput and Error Rate
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Performance Test Results - Throughput & Reliability', fontsize=16, fontweight='bold')
    
    # Throughput over time (queries per second)
    ax1 = axes[0, 0]
    df['time_window'] = df['timestamp'].dt.floor('10S')
    throughput = df.groupby('time_window').size() / 10  # queries per second
    ax1.plot(throughput.index, throughput.values, marker='o', linewidth=2, markersize=4, color='#6A994E')
    ax1.axhline(y=throughput.mean(), color='r', linestyle='--', label=f'Mean: {throughput.mean():.2f} req/s')
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Throughput (requests/second)')
    ax1.set_title('Throughput Over Time')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    
    # Error rate over time
    ax2 = axes[0, 1]
    if 'success' in df.columns:
        df['error'] = ~df['success']
        error_rate = df.groupby('time_window')['error'].mean() * 100
        ax2.plot(error_rate.index, error_rate.values, marker='o', linewidth=2, markersize=4, color='#C73E1D')
        ax2.axhline(y=error_rate.mean(), color='r', linestyle='--', label=f'Mean: {error_rate.mean():.2f}%')
        ax2.set_xlabel('Time')
        ax2.set_ylabel('Error Rate (%)')
        ax2.set_title('Error Rate Over Time')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
    
    # Success vs Failed queries
    ax3 = axes[1, 0]
    if 'success' in df.columns:
        success_count = df['success'].sum()
        failed_count = (~df['success']).sum()
        colors = ['#6A994E', '#C73E1D']
        ax3.pie([success_count, failed_count], labels=['Success', 'Failed'], 
                autopct='%1.1f%%', colors=colors, startangle=90, textprops={'fontsize': 12, 'fontweight': 'bold'})
        ax3.set_title(f'Query Success Rate\n(Total: {len(df)} queries)')
    
    # Response length distribution
    ax4 = axes[1, 1]
    if 'response_length' in df.columns:
        ax4.hist(df['response_length'], bins=50, color='#2E86AB', edgecolor='black', alpha=0.7)
        ax4.axvline(x=df['response_length'].mean(), color='r', linestyle='--', linewidth=2, 
                   label=f'Mean: {df["response_length"].mean():.0f} chars')
        ax4.set_xlabel('Response Length (characters)')
        ax4.set_ylabel('Frequency')
        ax4.set_title('Response Length Distribution')
        ax4.legend()
        ax4.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'throughput_reliability.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 3. Quality and User Activity
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Performance Test Results - Quality & User Activity', fontsize=16, fontweight='bold')
    
    # Quality score over time
    ax1 = axes[0, 0]
    if 'quality_score' in df.columns:
        ax1.scatter(df['timestamp'], df['quality_score'], alpha=0.5, s=20, color='#A23B72')
        ax1.axhline(y=df['quality_score'].mean(), color='r', linestyle='--', linewidth=2, 
                   label=f'Mean: {df["quality_score"].mean():.2f}')
        ax1.set_xlabel('Time')
        ax1.set_ylabel('Quality Score')
        ax1.set_title('Response Quality Over Time')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    
    # User activity (queries per user)
    ax2 = axes[0, 1]
    if 'user_id' in df.columns:
        user_activity = df.groupby('user_id').size().sort_values(ascending=False)
        top_users = user_activity.head(15)
        ax2.barh(range(len(top_users)), top_users.values, color='#2E86AB', edgecolor='black', alpha=0.7)
        ax2.set_yticks(range(len(top_users)))
        ax2.set_yticklabels([f'User {i+1}' for i in range(len(top_users))])
        ax2.set_xlabel('Number of Queries')
        ax2.set_title('Top 15 Users by Query Count')
        ax2.grid(True, alpha=0.3, axis='x')
        # Add value labels
        for i, v in enumerate(top_users.values):
            ax2.text(v, i, f' {v}', va='center', fontweight='bold')
    
    # Concurrent users over time
    ax3 = axes[1, 0]
    if 'user_id' in df.columns:
        concurrent_users = df.groupby('time_window')['user_id'].nunique()
        ax3.plot(concurrent_users.index, concurrent_users.values, marker='o', linewidth=2, 
                markersize=4, color='#F18F01')
        ax3.axhline(y=concurrent_users.mean(), color='r', linestyle='--', 
                   label=f'Mean: {concurrent_users.mean():.1f} users')
        ax3.set_xlabel('Time')
        ax3.set_ylabel('Concurrent Users')
        ax3.set_title('Concurrent Users Over Time')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)
    
    # Query type distribution
    ax4 = axes[1, 1]
    if 'query_type' in df.columns:
        query_types = df['query_type'].value_counts()
        colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E']
        ax4.pie(query_types.values, labels=query_types.index, autopct='%1.1f%%', 
               colors=colors[:len(query_types)], startangle=90, textprops={'fontsize': 10, 'fontweight': 'bold'})
        ax4.set_title('Query Type Distribution')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'quality_user_activity.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 4. System Utilization Dashboard
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Performance Test Results - System Utilization Dashboard', fontsize=16, fontweight='bold')
    
    # Response time vs throughput
    ax1 = axes[0, 0]
    if 'response_time' in df.columns:
        df['time_window'] = df['timestamp'].dt.floor('10S')
        window_stats = df.groupby('time_window').agg({
            'response_time': 'mean',
        })
        window_stats['throughput'] = df.groupby('time_window').size() / 10
        ax1.scatter(window_stats['throughput'], window_stats['response_time'], 
                   alpha=0.6, s=50, color='#2E86AB', edgecolors='black', linewidth=0.5)
        ax1.set_xlabel('Throughput (requests/second)')
        ax1.set_ylabel('Average Response Time (seconds)')
        ax1.set_title('Response Time vs Throughput')
        ax1.grid(True, alpha=0.3)
    
    # NFR Compliance
    ax2 = axes[0, 1]
    nfr_metrics = {
        'P95 Response Time < 30s': df['response_time'].quantile(0.95) < 30,
        'Error Rate < 5%': (df['success'] == False).mean() * 100 < 5 if 'success' in df.columns else False,
        'Throughput > 2 req/s': throughput.mean() > 2,
        'Quality Score > 60': df['quality_score'].mean() > 60 if 'quality_score' in df.columns else False,
        'First Chunk < 5s': df['first_chunk_time'].mean() < 5 if 'first_chunk_time' in df.columns else False,
    }
    colors = ['#6A994E' if v else '#C73E1D' for v in nfr_metrics.values()]
    bars = ax2.barh(range(len(nfr_metrics)), [1]*len(nfr_metrics), color=colors, edgecolor='black', alpha=0.7)
    ax2.set_yticks(range(len(nfr_metrics)))
    ax2.set_yticklabels(list(nfr_metrics.keys()))
    ax2.set_xlim(0, 1.2)
    ax2.set_title('NFR Compliance Status')
    ax2.grid(True, alpha=0.3, axis='x')
    # Add status labels
    for i, (metric, status) in enumerate(nfr_metrics.items()):
        ax2.text(0.5, i, '✓ PASS' if status else '✗ FAIL', 
                ha='center', va='center', fontweight='bold', fontsize=12,
                color='white' if status else 'white')
    
    # Response time by query type
    ax3 = axes[1, 0]
    if 'query_type' in df.columns:
        query_type_stats = df.groupby('query_type')['response_time'].agg(['mean', 'std']).sort_values('mean')
        x_pos = np.arange(len(query_type_stats))
        bars = ax3.bar(x_pos, query_type_stats['mean'], yerr=query_type_stats['std'], 
                      color='#A23B72', edgecolor='black', alpha=0.7, capsize=5)
        ax3.set_xticks(x_pos)
        ax3.set_xticklabels(query_type_stats.index, rotation=45, ha='right')
        ax3.set_ylabel('Response Time (seconds)')
        ax3.set_title('Average Response Time by Query Type')
        ax3.grid(True, alpha=0.3, axis='y')
        # Add value labels
        for i, (bar, val) in enumerate(zip(bars, query_type_stats['mean'])):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{val:.2f}s', ha='center', va='bottom', fontweight='bold')
    
    # System load summary
    ax4 = axes[1, 1]
    summary_data = {
        'Total Queries': len(df),
        'Avg Response Time': f"{df['response_time'].mean():.2f}s",
        'P95 Response Time': f"{df['response_time'].quantile(0.95):.2f}s",
        'Throughput': f"{throughput.mean():.2f} req/s",
        'Error Rate': f"{(~df['success']).mean()*100:.2f}%" if 'success' in df.columns else "N/A",
    }
    ax4.axis('off')
    table_text = '\n'.join([f"{k}: {v}" for k, v in summary_data.items()])
    ax4.text(0.5, 0.5, table_text, ha='center', va='center', fontsize=14, 
            fontweight='bold', family='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    ax4.set_title('System Load Summary')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'system_utilization.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✅ Created 4 visualization files in {output_dir}")

def generate_summary_report(results, output_dir):
    """Generate comprehensive summary report"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    summary = create_summary_stats(results)
    queries = results.get('queries', [])
    
    report = f"""# Performance Test Results - Executive Summary

**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Test Duration:** {summary['test_duration']:.2f} seconds ({summary['test_duration']/60:.2f} minutes)

## Key Metrics

### User Activity
- **Total Users:** {summary['total_users']}
- **Total Queries:** {summary['total_queries']}
- **Successful Queries:** {summary['successful_queries']}
- **Failed Queries:** {summary['failed_queries']}
- **Success Rate:** {(summary['successful_queries']/summary['total_queries']*100):.2f}%

### Performance Metrics
- **Average Response Time:** {summary['avg_response_time']:.2f} seconds
- **P95 Response Time:** {summary['p95_response_time']:.2f} seconds
- **P99 Response Time:** {summary['p99_response_time']:.2f} seconds
- **Average Time to First Chunk:** {summary['avg_first_chunk_time']:.2f} seconds
- **Throughput:** {summary['throughput']:.2f} requests/second
- **Error Rate:** {summary['error_rate']:.2f}%

### Quality Metrics
- **Average Response Length:** {summary['avg_response_length']:.0f} characters
- **Average Quality Score:** {summary['avg_quality_score']:.2f}/100

## NFR Compliance

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| P95 Response Time | < 30s | {summary['p95_response_time']:.2f}s | {'✅ PASS' if summary['p95_response_time'] < 30 else '❌ FAIL'} |
| Error Rate | < 5% | {summary['error_rate']:.2f}% | {'✅ PASS' if summary['error_rate'] < 5 else '❌ FAIL'} |
| Throughput | > 2 req/s | {summary['throughput']:.2f} req/s | {'✅ PASS' if summary['throughput'] > 2 else '❌ FAIL'} |
| Quality Score | > 60 | {summary['avg_quality_score']:.2f} | {'✅ PASS' if summary['avg_quality_score'] > 60 else '❌ FAIL'} |
| First Chunk Time | < 5s | {summary['avg_first_chunk_time']:.2f}s | {'✅ PASS' if summary['avg_first_chunk_time'] < 5 else '❌ FAIL'} |

## System Utilization

- **Peak Concurrent Users:** {max([q.get('concurrent_users', 0) for q in queries]) if queries else 0}
- **Average Concurrent Users:** {np.mean([q.get('concurrent_users', 0) for q in queries]) if queries else 0:.1f}
- **Peak Throughput:** {max([q.get('throughput', 0) for q in queries]) if queries else 0:.2f} req/s

## Recommendations

"""
    
    # Add recommendations based on results
    if summary['p95_response_time'] > 30:
        report += "- ⚠️  **Response Time:** P95 response time exceeds 30s target. Consider optimizing agent processing or increasing resources.\n"
    if summary['error_rate'] > 5:
        report += "- ⚠️  **Error Rate:** Error rate exceeds 5% target. Investigate and fix failing queries.\n"
    if summary['throughput'] < 2:
        report += "- ⚠️  **Throughput:** Throughput below 2 req/s target. Consider horizontal scaling.\n"
    if summary['avg_quality_score'] < 60:
        report += "- ⚠️  **Quality:** Average quality score below 60. Review agent responses and prompts.\n"
    
    if summary['p95_response_time'] <= 30 and summary['error_rate'] <= 5 and summary['throughput'] >= 2:
        report += "- ✅ **System Performance:** All key NFRs are met. System is ready for production load.\n"
    
    report += f"""
## Visualizations

The following visualizations have been generated:
1. `response_time_analysis.png` - Response time distribution and trends
2. `throughput_reliability.png` - Throughput and error rate analysis
3. `quality_user_activity.png` - Quality scores and user activity patterns
4. `system_utilization.png` - System utilization dashboard

## Detailed Data

Full test results are available in: `{results.get('output_file', 'N/A')}`
"""
    
    with open(output_dir / 'EXECUTIVE_SUMMARY.md', 'w') as f:
        f.write(report)
    
    print(f"✅ Generated executive summary: {output_dir / 'EXECUTIVE_SUMMARY.md'}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze-performance-results.py <results_json_file> [output_dir]")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else '/tmp/performance-analysis'
    
    print(f"📊 Loading results from {json_file}...")
    results = load_results(json_file)
    
    print("📈 Creating visualizations...")
    create_visualizations(results, output_dir)
    
    print("📝 Generating executive summary...")
    generate_summary_report(results, output_dir)
    
    print(f"\n✅ Analysis complete! Results saved to: {output_dir}")

if __name__ == '__main__':
    main()

