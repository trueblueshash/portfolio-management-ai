const STORAGE_KEY = 'app_api_key';

export default function LogoutButton({ className = '' }: { className?: string }) {
  return (
    <button
      type="button"
      onClick={() => {
        localStorage.removeItem(STORAGE_KEY);
        window.location.reload();
      }}
      className={`text-xs text-gray-400 hover:text-gray-600 font-medium ${className}`}
    >
      Logout
    </button>
  );
}
