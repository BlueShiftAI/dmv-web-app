import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate, Link } from "react-router-dom";
import { api } from "../api/client";
import { useAuthStore } from "../features/auth/authStore";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  full_name: z.string().min(2, "Enter your full name"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});
type FormData = z.infer<typeof schema>;

export default function RegisterPage() {
  const { register, handleSubmit, formState: { errors, isSubmitting }, setError } = useForm<FormData>({
    resolver: zodResolver(schema),
  });
  const setAuth = useAuthStore((s) => s.setAuth);
  const navigate = useNavigate();

  const onSubmit = async (data: FormData) => {
    try {
      const resp = await api.post("/api/auth/register", { ...data, role: "customer" });
      const { access_token, user_id, role, full_name } = resp.data;
      setAuth(access_token, user_id, role, full_name);
      navigate("/dashboard");
    } catch (err: any) {
      const msg = err.response?.data?.detail ?? "Registration failed.";
      setError("root", { message: msg });
    }
  };

  return (
    <div className="max-w-md mx-auto">
      <h1 className="mb-6">Create Account</h1>
      <form onSubmit={handleSubmit(onSubmit)} className="card space-y-4" noValidate>
        <div>
          <label htmlFor="full_name" className="label">Full name</label>
          <input id="full_name" type="text" className="input" autoComplete="name" {...register("full_name")} />
          {errors.full_name && <p className="text-red-600 text-xs mt-1" role="alert">{errors.full_name.message}</p>}
        </div>
        <div>
          <label htmlFor="email" className="label">Email</label>
          <input id="email" type="email" className="input" autoComplete="email" {...register("email")} />
          {errors.email && <p className="text-red-600 text-xs mt-1" role="alert">{errors.email.message}</p>}
        </div>
        <div>
          <label htmlFor="password" className="label">Password</label>
          <input id="password" type="password" className="input" autoComplete="new-password" {...register("password")} />
          {errors.password && <p className="text-red-600 text-xs mt-1" role="alert">{errors.password.message}</p>}
        </div>
        {errors.root && <p className="text-red-600 text-sm" role="alert">{errors.root.message}</p>}
        <button type="submit" className="btn-primary w-full" disabled={isSubmitting}>
          {isSubmitting ? "Creating account…" : "Create account"}
        </button>
        <p className="text-sm text-center text-gray-600">
          Already have an account? <Link to="/login" className="text-brand-600 hover:underline">Sign in</Link>
        </p>
      </form>
    </div>
  );
}
