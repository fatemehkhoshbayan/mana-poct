interface ILayoutProps {
  children: React.ReactNode;
}

export const Layout = ({ children }: ILayoutProps) => {
  return (
    <>
      <header className="mx-auto flex w-full max-w-5xl items-center justify-between py-6">
        <h1 className="text-4xl font-bold tracking-tight">Mana POCT</h1>
        <p className="mt-2 text-sm text-slate-400">QC Assistant</p>
      </header>
      <main className="mx-auto flex min-h-[80vh] w-full max-w-lg flex-col items-center justify-center gap-6">
        {children}
      </main>
      <footer className="fixed bottom-0 w-full py-6">
        <p className="text-center text-xs text-slate-600">Copyright 2026 Mana POCT</p>
      </footer>
    </>
  );
};

export default Layout;
