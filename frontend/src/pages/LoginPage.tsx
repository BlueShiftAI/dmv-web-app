import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate, Link } from "react-router-dom";
import { api } from "../api/client";
import { useAuthStore } from "../features/auth/authStore";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});
type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const { register, handleSubmit, formState: { errors, isSubmitting }, setError } = useForm<FormData>({
    resolver: zodResolver(schema),
  });
  const setAuth = useAuthStore((s) => s.setAuth);
  const navigate = useNavigate();

  const onSubmit = async (data: FormData) => {
    try {
      const params = new URLSearchParams({ username: data.email, password: data.password });
      const resp = await api.post("/api/auth/login", params, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      const { access_token, user_id, role, full_name } = resp.data;
      setAuth(access_token, user_id, role, full_name);
      navigate(role === "staff" || role === "admin" ? "/staff" : "/dashboard");
    } catch {
      setError("root", { message: "Invalid email or password." });
    }
  };

  return (
    <div className="max-w-md mx-auto">
      <h1 className="mb-6">Sign In</h1>
      <form onSubmit={handleSubmit(onSubmit)} className="card space-y-4" noValidate>
        <div>
          <label htmlFor="email" className="label">Email</label>
          <input id="email" type="email" className="input" autoComplete="email" {...register("email")} />
          {errors.email && <p className="text-red-600 text-xs mt-1" role="alert">{errors.email.message}</p>}
        </div>
        <div>
          <label htmlFor="password" className="label">Password</label>
          <input id="password" type="password" className="input" autoComplete="current-password" {...register("password")} />
          {errors.password && <p className="text-red-600 text-xs mt-1" role="alert">{errors.password.message}</p>}
        </div>
        {errors.root && <p className="text-red-600 text-sm" role="alert">{errors.root.message}</p>}
        <button type="submit" className="btn-primary w-full" disabled={isSubmitting}>
          {isSubmitting ? "Signing in…" : "Sign in"}
        </button>
        <p className="text-sm text-center text-gray-600">
          No account? <Link to="/register" className="text-brand-600 hover:underline">Register</Link>
        </p>
      </form>
    </div>
  );
}
