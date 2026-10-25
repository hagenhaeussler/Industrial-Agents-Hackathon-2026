import { X } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";

/** A native modal dialog: a bottom sheet on phones, a centred card on wide screens. */
export function Sheet({
  open,
  onClose,
  title,
  subtitle,
  children,
  className = "",
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    if (open && !element.open) element.showModal();
    if (!open && element.open) element.close();
  }, [open]);

  return (
    <dialog
      ref={dialog}
      className={`sheet ${className}`}
      onClose={onClose}
      onClick={(event) => event.target === dialog.current && onClose()}
      aria-label={title}
    >
      <div className="mx-auto mb-4 h-1 w-8 rounded-full bg-[#d9ddd1] min-[800px]:hidden" />
      <header className="mb-5 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-[24px] leading-tight font-[750] tracking-[-0.9px]">{title}</h2>
          {subtitle && <p className="mt-1.5 text-xs text-muted">{subtitle}</p>}
        </div>
        <IconButton label="Close" onClick={onClose}>
          <X size={20} />
        </IconButton>
      </header>
      {children}
    </dialog>
  );
}

export function IconButton({
  label,
  onClick,
  children,
  className = "bg-field",
  pressed,
}: {
  label: string;
  onClick: () => void;
  children: ReactNode;
  className?: string;
  pressed?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      aria-pressed={pressed}
      className={`grid size-11 shrink-0 place-items-center rounded-[13px] ${className}`}
    >
      {children}
    </button>
  );
}
