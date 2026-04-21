const APP_URL = (import.meta.env.VITE_APP_URL as string | undefined) ?? "https://app.zima.app";

export function Header() {
  return (
    <div className="flex items-center gap-2 px-4 py-3 border-b border-border shrink-0 bg-backdrop">
      <button
        onClick={() => chrome.tabs.create({ url: `${APP_URL}/dashboard` })}
        className="flex items-center gap-2 cursor-pointer bg-transparent border-0 p-0"
      >
        <svg className="w-4 h-4 text-primary" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z" />
        </svg>
        <span className="text-sm font-black tracking-widest text-primary">ZIMA</span>
      </button>
    </div>
  );
}
