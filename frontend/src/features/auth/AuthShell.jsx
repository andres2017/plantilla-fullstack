import { Link } from "react-router-dom";
import { Cube } from "@phosphor-icons/react";
import { APP_NAME } from "@/config";

export const AuthShell = ({ children, title, subtitle }) => (
  <div className="min-h-screen bg-background grid lg:grid-cols-2">
    <div className="hidden lg:flex flex-col justify-between border-r border-border bg-[#002FA7] p-12">
      <Link to="/" className="flex items-center gap-3" data-testid="auth-brand-link">
        <Cube size={28} weight="fill" className="text-white" />
        <span className="font-heading text-xl font-black tracking-tighter text-white">{APP_NAME}</span>
      </Link>
      <div>
        <h1 className="font-heading text-5xl xl:text-6xl font-black tracking-tighter text-white leading-[0.95]">
          Tu producto.<br />A tu ritmo.
        </h1>
        <p className="mt-6 max-w-md text-base leading-relaxed text-white/70">
          Backend en capas + frontend por features, listos para crecer.
        </p>
      </div>
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-white/50">
        v0.1.0 — plantilla base
      </p>
    </div>
    <div className="flex items-center justify-center p-6 sm:p-12">
      <div className="w-full max-w-md">
        <div className="lg:hidden mb-10 flex items-center gap-2">
          <Cube size={24} weight="fill" className="text-[#002FA7]" />
          <span className="font-heading text-lg font-black tracking-tighter">{APP_NAME}</span>
        </div>
        <h2 className="font-heading text-3xl font-black tracking-tighter">{title}</h2>
        <p className="mt-2 text-sm text-muted-foreground">{subtitle}</p>
        <div className="mt-8">{children}</div>
      </div>
    </div>
  </div>
);
