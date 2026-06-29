interface ILayoutProps {
  children: React.ReactNode;
}

export const Layout = ({ children }: ILayoutProps) => {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="mx-auto flex w-full max-w-5xl items-center justify-between py-6">
        <h1 className="text-4xl font-bold tracking-tight">Mana POCT</h1>
        <p className="mt-2 text-sm text-slate-400">QC Assistant</p>
      </header>
      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col items-center justify-start gap-6 pb-4">
        {children}
      </main>
      <footer className="w-full py-4">
        <p className="text-center text-xs text-slate-600">Copyright 2026 Mana POCT</p>
      </footer>
    </div>
  );
};

export default Layout;
