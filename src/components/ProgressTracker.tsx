import { CheckCircle2, Circle, AlertCircle } from 'lucide-react';

interface Stage {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  message?: string;
}

interface ProgressTrackerProps {
  stages: Stage[];
}

export function ProgressTracker({ stages }: ProgressTrackerProps) {
  return (
    <div className="w-full max-w-3xl mx-auto bg-white rounded-2xl shadow-lg p-8">
      <h3 className="text-xl font-bold text-gray-900 mb-6">AI Agents Processing</h3>

      <div className="space-y-4">
        {stages.map((stage, index) => (
          <div key={stage.id} className="flex items-start gap-4">
            <div className="flex-shrink-0 mt-1">
              {stage.status === 'completed' && (
                <CheckCircle2 className="w-6 h-6 text-green-500" />
              )}
              {stage.status === 'processing' && (
                <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              )}
              {stage.status === 'pending' && (
                <Circle className="w-6 h-6 text-gray-300" />
              )}
              {stage.status === 'error' && (
                <AlertCircle className="w-6 h-6 text-red-500" />
              )}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <h4 className={`font-semibold ${
                  stage.status === 'completed' ? 'text-green-700' :
                  stage.status === 'processing' ? 'text-blue-700' :
                  stage.status === 'error' ? 'text-red-700' :
                  'text-gray-500'
                }`}>
                  {stage.name}
                </h4>
                {stage.status === 'processing' && (
                  <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded-full">
                    In Progress
                  </span>
                )}
              </div>

              <p className={`text-sm mt-1 ${
                stage.status === 'error' ? 'text-red-600' : 'text-gray-600'
              }`}>
                {stage.message || stage.description}
              </p>
            </div>

            {index < stages.length - 1 && (
              <div className="absolute left-[35px] w-0.5 h-8 bg-gray-200 mt-8" />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
