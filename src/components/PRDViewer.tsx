import { Download, FileText, CheckCircle, AlertTriangle, Info } from 'lucide-react';
import type { PRDContent, ValidationOutput } from '../agents/types';

interface PRDViewerProps {
  prd: PRDContent;
  validation?: ValidationOutput;
}

export function PRDViewer({ prd, validation }: PRDViewerProps) {
  const downloadPRD = () => {
    const content = JSON.stringify(prd, null, 2);
    const blob = new Blob([content], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${prd.overview.title.replace(/\s+/g, '_')}_PRD.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="w-full max-w-6xl mx-auto space-y-6">
      {validation && (
        <div className="bg-white rounded-2xl shadow-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-gray-900">Quality Assessment</h3>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-600">Completeness:</span>
              <span className="text-2xl font-bold text-blue-600">{validation.completeness}%</span>
            </div>
          </div>

          {validation.issues.length > 0 && (
            <div className="space-y-2 mb-4">
              {validation.issues.map((issue, idx) => (
                <div
                  key={idx}
                  className={`flex items-start gap-3 p-3 rounded-lg ${
                    issue.severity === 'critical' ? 'bg-red-50 border border-red-200' :
                    issue.severity === 'warning' ? 'bg-yellow-50 border border-yellow-200' :
                    'bg-blue-50 border border-blue-200'
                  }`}
                >
                  {issue.severity === 'critical' && <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />}
                  {issue.severity === 'warning' && <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />}
                  {issue.severity === 'info' && <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />}
                  <div className="flex-1">
                    <p className="font-medium text-sm text-gray-900">
                      {issue.section}: {issue.message}
                    </p>
                    <p className="text-sm text-gray-600 mt-1">{issue.suggestion}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {validation.recommendations.length > 0 && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <h4 className="font-semibold text-green-900 mb-2 flex items-center gap-2">
                <CheckCircle className="w-5 h-5" />
                Recommendations
              </h4>
              <ul className="list-disc list-inside space-y-1">
                {validation.recommendations.map((rec, idx) => (
                  <li key={idx} className="text-sm text-green-800">{rec}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
        <div className="bg-gradient-to-r from-blue-500 to-blue-600 px-8 py-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FileText className="w-8 h-8 text-white" />
            <div>
              <h2 className="text-2xl font-bold text-white">{prd.overview.title}</h2>
              <p className="text-blue-100">Version {prd.overview.version} • {prd.overview.date}</p>
            </div>
          </div>
          <button
            onClick={downloadPRD}
            className="px-4 py-2 bg-white text-blue-600 font-medium rounded-lg hover:bg-blue-50 transition flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Download
          </button>
        </div>

        <div className="p-8 space-y-8">
          <section>
            <h3 className="text-xl font-bold text-gray-900 mb-3">Executive Summary</h3>
            <p className="text-gray-700 leading-relaxed">{prd.overview.summary}</p>
          </section>

          <section>
            <h3 className="text-xl font-bold text-gray-900 mb-3">Problem Statement</h3>
            <p className="text-gray-700 leading-relaxed">{prd.problemStatement}</p>
          </section>

          <section>
            <h3 className="text-xl font-bold text-gray-900 mb-3">Goals</h3>
            <ul className="list-disc list-inside space-y-2">
              {prd.goals.map((goal, idx) => (
                <li key={idx} className="text-gray-700">{goal}</li>
              ))}
            </ul>
          </section>

          <section>
            <h3 className="text-xl font-bold text-gray-900 mb-4">Target Users</h3>
            <div className="grid gap-4 md:grid-cols-2">
              {prd.targetUsers.map((user, idx) => (
                <div key={idx} className="border border-gray-200 rounded-lg p-4">
                  <h4 className="font-semibold text-gray-900 mb-3">{user.persona}</h4>
                  <div className="space-y-2">
                    <div>
                      <p className="text-sm font-medium text-gray-600">Needs:</p>
                      <ul className="list-disc list-inside text-sm text-gray-700">
                        {user.needs.map((need, nIdx) => (
                          <li key={nIdx}>{need}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-600">Pain Points:</p>
                      <ul className="list-disc list-inside text-sm text-gray-700">
                        {user.painPoints.map((pain, pIdx) => (
                          <li key={pIdx}>{pain}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section>
            <h3 className="text-xl font-bold text-gray-900 mb-4">Features</h3>
            <div className="space-y-4">
              {prd.features.map((feature) => (
                <div key={feature.id} className="border border-gray-200 rounded-lg p-5">
                  <div className="flex items-start justify-between mb-3">
                    <h4 className="font-semibold text-lg text-gray-900">{feature.name}</h4>
                    <span className={`px-3 py-1 text-xs font-medium rounded-full ${
                      feature.priority === 'P0' ? 'bg-red-100 text-red-700' :
                      feature.priority === 'P1' ? 'bg-orange-100 text-orange-700' :
                      'bg-blue-100 text-blue-700'
                    }`}>
                      {feature.priority}
                    </span>
                  </div>
                  <p className="text-gray-700 mb-4">{feature.description}</p>

                  <div className="space-y-3">
                    <div>
                      <p className="text-sm font-medium text-gray-600 mb-2">User Stories:</p>
                      <ul className="list-disc list-inside space-y-1">
                        {feature.userStories.map((story, idx) => (
                          <li key={idx} className="text-sm text-gray-700">{story}</li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <p className="text-sm font-medium text-gray-600 mb-2">Acceptance Criteria:</p>
                      <ul className="list-disc list-inside space-y-1">
                        {feature.acceptanceCriteria.map((criteria, idx) => (
                          <li key={idx} className="text-sm text-gray-700">{criteria}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section>
            <h3 className="text-xl font-bold text-gray-900 mb-4">Technical Requirements</h3>
            <div className="space-y-4">
              <div>
                <h4 className="font-semibold text-gray-900 mb-2">Architecture</h4>
                <p className="text-gray-700">{prd.technicalRequirements.architecture}</p>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <h4 className="font-semibold text-gray-900 mb-2">Integrations</h4>
                  <ul className="list-disc list-inside text-sm text-gray-700">
                    {prd.technicalRequirements.integrations.map((int, idx) => (
                      <li key={idx}>{int}</li>
                    ))}
                  </ul>
                </div>

                <div>
                  <h4 className="font-semibold text-gray-900 mb-2">Security</h4>
                  <ul className="list-disc list-inside text-sm text-gray-700">
                    {prd.technicalRequirements.security.map((sec, idx) => (
                      <li key={idx}>{sec}</li>
                    ))}
                  </ul>
                </div>

                <div>
                  <h4 className="font-semibold text-gray-900 mb-2">Performance</h4>
                  <ul className="list-disc list-inside text-sm text-gray-700">
                    {prd.technicalRequirements.performance.map((perf, idx) => (
                      <li key={idx}>{perf}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </section>

          <section>
            <h3 className="text-xl font-bold text-gray-900 mb-4">Success Metrics</h3>
            <div className="grid gap-3 md:grid-cols-2">
              {prd.successMetrics.map((metric, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <span className="text-gray-700">{metric.metric}</span>
                  <span className="font-semibold text-blue-600">{metric.target}</span>
                </div>
              ))}
            </div>
          </section>

          <section>
            <h3 className="text-xl font-bold text-gray-900 mb-4">Timeline</h3>
            <div className="space-y-3">
              {prd.timeline.map((phase, idx) => (
                <div key={idx} className="border-l-4 border-blue-500 pl-4 py-2">
                  <div className="flex items-center gap-3 mb-2">
                    <h4 className="font-semibold text-gray-900">{phase.phase}</h4>
                    <span className="text-sm text-gray-600">{phase.duration}</span>
                  </div>
                  <ul className="list-disc list-inside text-sm text-gray-700">
                    {phase.deliverables.map((deliverable, dIdx) => (
                      <li key={dIdx}>{deliverable}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
