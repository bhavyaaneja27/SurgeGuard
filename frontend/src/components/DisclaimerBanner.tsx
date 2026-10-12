import { AlertTriangle } from 'lucide-react';

export const DisclaimerBanner: React.FC = () => {
  return (
    <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 text-xs text-amber-900 flex items-center justify-between">
      <div className="flex items-center space-x-2">
        <AlertTriangle className="w-4 h-4 text-amber-700 flex-shrink-0" />
        <span>
          <strong>RESEARCH PROTOTYPE / SYNTHETIC DATA:</strong> This platform evaluates marketplace integrity models using simulated data and synthetic driver availability patterns. It does not connect to live Uber systems, does not process private driver data, and does not prove legal collusion or wrongdoing.
        </span>
      </div>
      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-200 text-amber-900 uppercase tracking-wider ml-2 flex-shrink-0">
        Simulated Demo
      </span>
    </div>
  );
};
