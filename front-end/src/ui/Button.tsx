interface IButtonProps {
  onClick: () => void;
  disabled: boolean;
  children: React.ReactNode;
}

export default function Button({ onClick, disabled, children }: IButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="flex-1 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
    >
      {children}
    </button>
  );
}
