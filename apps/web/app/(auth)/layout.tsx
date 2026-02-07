export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-primary-900 via-primary-800 to-primary-700">
      <div className="w-full max-w-md px-4">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-white">PortiQ</h1>
          <p className="mt-2 text-primary-200">
            Maritime Procurement Platform
          </p>
        </div>
        {children}
      </div>
    </div>
  );
}
