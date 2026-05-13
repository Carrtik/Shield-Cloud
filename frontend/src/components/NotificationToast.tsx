import { CheckCircle2, XCircle, AlertTriangle, Info, X } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import type { Notification } from '../store/useAppStore';

const icons = {
  success: CheckCircle2,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};

const colors = {
  success: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300 shadow-[0_0_20px_rgba(16,185,129,0.15)]',
  error:   'border-danger/40 bg-danger/10 text-red-300 shadow-[0_0_20px_rgba(239,68,68,0.15)]',
  warning: 'border-warning/40 bg-warning/10 text-amber-300 shadow-[0_0_20px_rgba(245,158,11,0.15)]',
  info:    'border-primary/40 bg-primary/10 text-blue-300 shadow-[0_0_20px_rgba(59,130,246,0.15)]',
};

const ToastItem = ({ n }: { n: Notification }) => {
  const { removeNotification } = useAppStore();
  const Icon = icons[n.type];

  return (
    <div
      className={`flex items-start gap-3 px-4 py-3 rounded-xl border backdrop-blur-md max-w-sm w-full animate-in slide-in-from-right-4 fade-in duration-300 ${colors[n.type]}`}
    >
      <Icon className="w-4 h-4 mt-0.5 flex-shrink-0" />
      <p className="text-sm font-medium flex-1 leading-snug">{n.message}</p>
      <button onClick={() => removeNotification(n.id)} className="opacity-50 hover:opacity-100 transition-opacity flex-shrink-0 mt-0.5">
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
};

export const NotificationToast = () => {
  const { notifications } = useAppStore();

  if (notifications.length === 0) return null;

  return (
    <div className="fixed top-5 right-5 z-[100] flex flex-col gap-2 pointer-events-none">
      {notifications.map((n) => (
        <div key={n.id} className="pointer-events-auto">
          <ToastItem n={n} />
        </div>
      ))}
    </div>
  );
};
