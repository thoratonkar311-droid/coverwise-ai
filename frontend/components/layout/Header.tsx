"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/lib/auth-context";
import {
  ShieldCheck,
  Menu,
  X,
  User,
  ArrowRight,
  LogOut,
  ChevronDown,
  LayoutDashboard,
  FileUp,
} from "lucide-react";

export interface HeaderProps {
  className?: string;
}

export function Header({ className }: HeaderProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const pathname = usePathname();
  const { user, isAuthenticated, logout, openAuthModal } = useAuth();

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 8);
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Close user menu on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setUserMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Close mobile menu on resize to desktop
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 1024) {
        setMobileMenuOpen(false);
      }
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const navLinks = [
    { label: "Product", href: "/" },
    { label: "Policy Assistant", href: "/assistant" },
    { label: "Coverage Intelligence", href: "/coverage" },
    { label: "Treatment Costs", href: "/simulator" },
    { label: "Dashboard", href: "/dashboard" },
  ];

  return (
    <header
      className={cn(
        "sticky top-0 z-50 w-full transition-all duration-200",
        scrolled
          ? "bg-white/95 backdrop-blur-md shadow-[0_2px_12px_rgba(10,29,46,0.06)] border-b border-slate-200/80"
          : "bg-white/80 backdrop-blur-sm border-b border-slate-200/60",
        className
      )}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-18 sm:h-20 gap-4">
          {/* Brand Logo & Tagline */}
          <Link
            href="/"
            className="flex items-center gap-3 group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1769FF] rounded-xl p-1 -ml-1 transition-transform"
            aria-label="CoverWise AI — Policy-to-Patient Intelligence Home"
          >
            <div className="w-10 h-10 sm:w-11 sm:h-11 rounded-xl bg-gradient-to-br from-[#0052D1] via-[#1769FF] to-[#006B5F] flex items-center justify-center text-white shadow-md shadow-blue-500/20 group-hover:scale-105 transition-transform duration-200">
              <ShieldCheck className="w-6 h-6 stroke-[2.2]" />
            </div>

            <div className="flex flex-col">
              <div className="flex items-center gap-1.5">
                <span className="text-lg sm:text-xl font-bold tracking-tight text-[#0A1D2E]">
                  CoverWise<span className="text-[#1769FF]">.ai</span>
                </span>
              </div>
              <span className="text-[11px] sm:text-xs text-slate-500 font-medium tracking-tight">
                Policy-to-Patient Intelligence
              </span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav
            aria-label="Main Navigation"
            className="hidden lg:flex items-center gap-1 xl:gap-2"
          >
            {navLinks.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.label}
                  href={link.href}
                  className={cn(
                    "text-xs xl:text-sm font-medium px-3 py-2 rounded-lg transition-colors duration-150 select-none",
                    isActive
                      ? "text-[#0052D1] bg-[#EEF4FF] font-semibold"
                      : "text-slate-600 hover:text-[#0052D1] hover:bg-slate-50"
                  )}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>

          {/* Right side actions */}
          <div className="hidden sm:flex items-center gap-2.5">
            {isAuthenticated && user ? (
              <div className="relative" ref={userMenuRef}>
                <button
                  type="button"
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-[#EEF4FF] hover:border-blue-200 text-slate-700 transition-colors cursor-pointer text-xs font-semibold"
                  aria-expanded={userMenuOpen}
                  aria-haspopup="true"
                >
                  <div className="w-6 h-6 rounded-full bg-[#0052D1] text-white flex items-center justify-center text-[11px] font-bold">
                    {user.email.charAt(0).toUpperCase()}
                  </div>
                  <span className="max-w-[120px] truncate">{user.fullName || user.email}</span>
                  <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                </button>

                {userMenuOpen && (
                  <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-xl border border-slate-200 py-1.5 z-50 animate-in fade-in zoom-in-95 duration-100">
                    <div className="px-3.5 py-2 border-b border-slate-100">
                      <p className="text-[11px] font-medium text-slate-400">Signed in as</p>
                      <p className="text-xs font-semibold text-slate-900 truncate">{user.email}</p>
                    </div>

                    <Link
                      href="/dashboard"
                      onClick={() => setUserMenuOpen(false)}
                      className="flex items-center gap-2 px-3.5 py-2 text-xs text-slate-700 hover:bg-[#EEF4FF] hover:text-[#0052D1] transition-colors"
                    >
                      <LayoutDashboard className="w-3.5 h-3.5" />
                      Intelligence Dashboard
                    </Link>

                    <Link
                      href="/analyze"
                      onClick={() => setUserMenuOpen(false)}
                      className="flex items-center gap-2 px-3.5 py-2 text-xs text-slate-700 hover:bg-[#EEF4FF] hover:text-[#0052D1] transition-colors"
                    >
                      <FileUp className="w-3.5 h-3.5" />
                      Upload New Policy
                    </Link>

                    <div className="my-1 border-t border-slate-100" />

                    <button
                      type="button"
                      onClick={() => {
                        setUserMenuOpen(false);
                        logout();
                      }}
                      className="flex w-full items-center gap-2 px-3.5 py-2 text-xs text-rose-600 hover:bg-rose-50 transition-colors cursor-pointer font-medium"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      Sign Out
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <Button
                variant="ghost"
                size="sm"
                className="text-slate-700 hover:text-[#0052D1]"
                onClick={() => openAuthModal("login")}
              >
                Sign In
              </Button>
            )}

            <Link href="/analyze">
              <Button
                variant="primary"
                size="sm"
                rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
                className="shadow-sm font-semibold"
              >
                Analyze My Policy
              </Button>
            </Link>

            {!isAuthenticated && (
              <button
                type="button"
                onClick={() => openAuthModal("login")}
                className="w-9 h-9 rounded-xl border border-slate-200 bg-slate-50 hover:bg-[#EEF4FF] hover:border-blue-200 text-slate-600 hover:text-[#0052D1] flex items-center justify-center transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1769FF]"
                aria-label="User Account"
                title="Sign In"
              >
                <User className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Mobile Menu Button */}
          <div className="flex items-center gap-2 lg:hidden">
            <button
              type="button"
              onClick={() => {
                if (isAuthenticated) {
                  setUserMenuOpen(!userMenuOpen);
                } else {
                  openAuthModal("login");
                }
              }}
              className="w-9 h-9 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 flex items-center justify-center transition-colors cursor-pointer sm:hidden"
              aria-label="User Profile"
            >
              <User className="w-4 h-4" />
            </button>

            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="w-10 h-10 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-800 flex items-center justify-center transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1769FF]"
              aria-label={mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
              aria-expanded={mobileMenuOpen}
            >
              {mobileMenuOpen ? (
                <X className="w-5 h-5 text-slate-800" />
              ) : (
                <Menu className="w-5 h-5 text-slate-800" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer Navigation */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-b border-slate-200 bg-white/98 backdrop-blur-md px-4 pt-3 pb-6 space-y-4 shadow-xl animate-in slide-in-from-top-2 duration-200">
          <nav aria-label="Mobile Navigation" className="flex flex-col gap-1">
            {navLinks.map((link) => (
              <Link
                key={link.label}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className="text-sm font-medium text-slate-700 hover:text-[#0052D1] hover:bg-[#EEF4FF] px-3.5 py-2.5 rounded-xl transition-colors"
              >
                {link.label}
              </Link>
            ))}
          </nav>

          <div className="pt-3 border-t border-slate-100 flex flex-col gap-2.5">
            {isAuthenticated && user ? (
              <div className="space-y-2">
                <div className="px-3 py-2 bg-slate-50 rounded-xl border border-slate-200/80">
                  <p className="text-[11px] text-slate-400 font-medium">Logged in as</p>
                  <p className="text-xs font-bold text-slate-800 truncate">{user.email}</p>
                </div>
                <Button
                  variant="outline"
                  size="md"
                  className="w-full justify-center text-rose-600 border-rose-200 hover:bg-rose-50"
                  onClick={() => {
                    setMobileMenuOpen(false);
                    logout();
                  }}
                >
                  <LogOut className="w-4 h-4 mr-2" />
                  Sign Out
                </Button>
              </div>
            ) : (
              <Button
                variant="outline"
                size="md"
                className="w-full justify-center text-slate-800 border-slate-300"
                onClick={() => {
                  setMobileMenuOpen(false);
                  openAuthModal("login");
                }}
              >
                Sign In / Register
              </Button>
            )}

            <Link
              href="/analyze"
              onClick={() => setMobileMenuOpen(false)}
              className="w-full"
            >
              <Button
                variant="primary"
                size="md"
                className="w-full justify-center"
                rightIcon={<ArrowRight className="w-4 h-4" />}
              >
                Analyze My Policy
              </Button>
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}

