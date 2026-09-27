import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { HeroSection } from "@/components/sections/HeroSection";
import { ProblemSection } from "@/components/sections/ProblemSection";
import { HowItWorksSection } from "@/components/sections/HowItWorksSection";
import { DashboardPreviewSection } from "@/components/sections/DashboardPreviewSection";
import { DesignSystemShowcase } from "@/components/sections/DesignSystemShowcase";
import { FinalCTASection } from "@/components/sections/FinalCTASection";

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FF] text-[#0A1D2E] antialiased selection:bg-[#EEF4FF] selection:text-[#0052D1]">
      {/* 1. Header Navigation */}
      <Header />

      {/* Main Content Sections */}
      <main className="flex-1">
        {/* 2 & 3. Hero Section with Messaging & Hero Intelligence Visualization */}
        <HeroSection />

        {/* 4. Problem Section: The Coverage Clarity Gap */}
        <ProblemSection />

        {/* 5. How It Works: 5-Stage Connected Workflow */}
        <HowItWorksSection />

        {/* Coverage Intelligence & Treatment Cost Simulator */}
        <DashboardPreviewSection />

        {/* Foundational Design System Component Showcase */}
        <DesignSystemShowcase />

        {/* 6. Final Call-To-Action with Mandatory Disclaimer */}
        <FinalCTASection />
      </main>

      {/* Footer with Transparency Guidelines & Notice */}
      <Footer />
    </div>
  );
}
