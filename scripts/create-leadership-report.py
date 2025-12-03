#!/usr/bin/env python3
"""
Create comprehensive leadership report with visualizations
Works without matplotlib if needed, creates HTML report
"""
import json
import sys
from pathlib import Path
from datetime import datetime
import statistics

def load_results(json_file):
    """Load performance test results"""
    with open(json_file, 'r') as f:
        return json.load(f)

def create_html_report(results, output_file):
    """Create HTML report with embedded charts using Chart.js"""
    
    queries = results.get('queries', [])
    if not queries:
        return
    
    # Calculate metrics
    response_times = [q.get('response_time', 0) for q in queries if q.get('response_time')]
    first_chunk_times = [q.get('first_chunk_time', 0) for q in queries if q.get('first_chunk_time')]
    quality_scores = [q.get('quality_score', 0) for q in queries if q.get('quality_score')]
    
    avg_response_time = statistics.mean(response_times) if response_times else 0
    p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)] if response_times else 0
    p99_response_time = sorted(response_times)[int(len(response_times) * 0.99)] if response_times else 0
    avg_first_chunk = statistics.mean(first_chunk_times) if first_chunk_times else 0
    avg_quality = statistics.mean(quality_scores) if quality_scores else 0
    
    successful = sum(1 for q in queries if q.get('status_code') == 200)
    failed = len(queries) - successful
    error_rate = (failed / len(queries) * 100) if queries else 0
    
    test_duration = results.get('test_duration', 0)
    throughput = len(queries) / test_duration if test_duration > 0 else 0
    
    # Prepare time series data
    time_data = []
    response_time_data = []
    for q in sorted(queries, key=lambda x: x.get('timestamp', 0)):
        time_data.append(datetime.fromtimestamp(q.get('timestamp', 0)).strftime('%H:%M:%S'))
        response_time_data.append(q.get('response_time', 0))
    
    # Create HTML with Chart.js
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Performance Test Results - Executive Summary</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .metric-card.success {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }}
        .metric-card.warning {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }}
        .metric-value {{
            font-size: 32px;
            font-weight: bold;
            margin: 10px 0;
        }}
        .metric-label {{
            font-size: 14px;
            opacity: 0.9;
        }}
        .chart-container {{
            margin: 30px 0;
            padding: 20px;
            background: #fafafa;
            border-radius: 8px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #3498db;
            color: white;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
        .status-pass {{
            color: #27ae60;
            font-weight: bold;
        }}
        .status-fail {{
            color: #e74c3c;
            font-weight: bold;
        }}
        .summary-box {{
            background: #ecf0f1;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 5px solid #3498db;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Performance Test Results - Executive Summary</h1>
        <p><strong>Test Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Test Duration:</strong> {test_duration:.2f} seconds ({test_duration/60:.2f} minutes)</p>
        
        <div class="summary-box">
            <h2>📊 Key Highlights</h2>
            <ul>
                <li><strong>Total Queries:</strong> {len(queries)}</li>
                <li><strong>Success Rate:</strong> {(successful/len(queries)*100):.2f}%</li>
                <li><strong>Average Response Time:</strong> {avg_response_time:.2f}s</li>
                <li><strong>Throughput:</strong> {throughput:.2f} requests/second</li>
                <li><strong>Quality Score:</strong> {avg_quality:.2f}/100</li>
            </ul>
        </div>
        
        <h2>📈 Performance Metrics</h2>
        <div class="metrics-grid">
            <div class="metric-card {'success' if avg_response_time < 5 else 'warning'}">
                <div class="metric-label">Average Response Time</div>
                <div class="metric-value">{avg_response_time:.2f}s</div>
            </div>
            <div class="metric-card {'success' if p95_response_time < 30 else 'warning'}">
                <div class="metric-label">P95 Response Time</div>
                <div class="metric-value">{p95_response_time:.2f}s</div>
            </div>
            <div class="metric-card {'success' if error_rate < 5 else 'warning'}">
                <div class="metric-label">Error Rate</div>
                <div class="metric-value">{error_rate:.2f}%</div>
            </div>
            <div class="metric-card {'success' if throughput > 2 else 'warning'}">
                <div class="metric-label">Throughput</div>
                <div class="metric-value">{throughput:.2f} req/s</div>
            </div>
            <div class="metric-card {'success' if avg_quality > 60 else 'warning'}">
                <div class="metric-label">Quality Score</div>
                <div class="metric-value">{avg_quality:.2f}/100</div>
            </div>
            <div class="metric-card {'success' if avg_first_chunk < 5 else 'warning'}">
                <div class="metric-label">First Chunk Time</div>
                <div class="metric-value">{avg_first_chunk:.2f}s</div>
            </div>
        </div>
        
        <h2>📊 Response Time Over Time</h2>
        <div class="chart-container">
            <canvas id="responseTimeChart"></canvas>
        </div>
        
        <h2>📊 Response Time Distribution</h2>
        <div class="chart-container">
            <canvas id="distributionChart"></canvas>
        </div>
        
        <h2>✅ NFR Compliance</h2>
        <table>
            <thead>
                <tr>
                    <th>Metric</th>
                    <th>Target</th>
                    <th>Actual</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>P95 Response Time</td>
                    <td>&lt; 30s</td>
                    <td>{p95_response_time:.2f}s</td>
                    <td class="{'status-pass' if p95_response_time < 30 else 'status-fail'}">{'✅ PASS' if p95_response_time < 30 else '❌ FAIL'}</td>
                </tr>
                <tr>
                    <td>Error Rate</td>
                    <td>&lt; 5%</td>
                    <td>{error_rate:.2f}%</td>
                    <td class="{'status-pass' if error_rate < 5 else 'status-fail'}">{'✅ PASS' if error_rate < 5 else '❌ FAIL'}</td>
                </tr>
                <tr>
                    <td>Throughput</td>
                    <td>&gt; 2 req/s</td>
                    <td>{throughput:.2f} req/s</td>
                    <td class="{'status-pass' if throughput > 2 else 'status-fail'}">{'✅ PASS' if throughput > 2 else '❌ FAIL'}</td>
                </tr>
                <tr>
                    <td>Quality Score</td>
                    <td>&gt; 60</td>
                    <td>{avg_quality:.2f}</td>
                    <td class="{'status-pass' if avg_quality > 60 else 'status-fail'}">{'✅ PASS' if avg_quality > 60 else '❌ FAIL'}</td>
                </tr>
                <tr>
                    <td>First Chunk Time</td>
                    <td>&lt; 5s</td>
                    <td>{avg_first_chunk:.2f}s</td>
                    <td class="{'status-pass' if avg_first_chunk < 5 else 'status-fail'}">{'✅ PASS' if avg_first_chunk < 5 else '❌ FAIL'}</td>
                </tr>
            </tbody>
        </table>
        
        <h2>🎯 System Utilization</h2>
        <div class="summary-box">
            <p><strong>Total Users:</strong> {results.get('total_users', 0)}</p>
            <p><strong>Total Queries:</strong> {len(queries)}</p>
            <p><strong>Successful Queries:</strong> {successful}</p>
            <p><strong>Failed Queries:</strong> {failed}</p>
            <p><strong>Peak Concurrent Users:</strong> {max([q.get('concurrent_users', 0) for q in queries]) if queries else 0}</p>
        </div>
    </div>
    
    <script>
        // Response Time Over Time Chart
        const ctx1 = document.getElementById('responseTimeChart').getContext('2d');
        new Chart(ctx1, {{
            type: 'line',
            data: {{
                labels: {json.dumps(time_data[:50])},  // Limit to 50 points for performance
                datasets: [{{
                    label: 'Response Time (seconds)',
                    data: {json.dumps(response_time_data[:50])},
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.1
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Response Time Over Time'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Response Time (seconds)'
                        }}
                    }}
                }}
            }}
        }});
        
        // Response Time Distribution Chart
        const ctx2 = document.getElementById('distributionChart').getContext('2d');
        const bins = 20;
        const minVal = Math.min(...{json.dumps(response_time_data)});
        const maxVal = Math.max(...{json.dumps(response_time_data)});
        const binSize = (maxVal - minVal) / bins;
        const histogram = Array(bins).fill(0);
        {json.dumps(response_time_data)}.forEach(val => {{
            const binIndex = Math.min(Math.floor((val - minVal) / binSize), bins - 1);
            histogram[binIndex]++;
        }});
        
        new Chart(ctx2, {{
            type: 'bar',
            data: {{
                labels: Array.from({{length: bins}}, (_, i) => (minVal + i * binSize).toFixed(2)),
                datasets: [{{
                    label: 'Frequency',
                    data: histogram,
                    backgroundColor: 'rgba(153, 102, 255, 0.6)',
                    borderColor: 'rgba(153, 102, 255, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Response Time Distribution'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Frequency'
                        }}
                    }},
                    x: {{
                        title: {{
                            display: true,
                            text: 'Response Time (seconds)'
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
    
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"✅ Created HTML report: {output_file}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 create-leadership-report.py <results_json_file> [output_html_file]")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else '/tmp/performance-analysis/LEADERSHIP_REPORT.html'
    
    print(f"📊 Loading results from {json_file}...")
    results = load_results(json_file)
    
    print("📝 Creating HTML report...")
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    create_html_report(results, output_file)
    
    print(f"\n✅ Report created: {output_file}")
    print(f"   Open in browser to view interactive charts")

if __name__ == '__main__':
    main()

