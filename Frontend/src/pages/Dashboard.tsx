import { Layout } from "@/components/Layout";
import { NetWorthWidget } from "@/components/widgets/NetWorthWidget";
import { TransactionsWidget } from "@/components/widgets/TransactionsWidget";
import { BudgetWidget } from "@/components/widgets/BudgetWidget";
import { SavingsGoalsWidget } from "@/components/widgets/SavingsGoalsWidget";
import { AIInsightsWidget } from "@/components/widgets/AIInsightsWidget";
import FIREWidget from "@/components/widgets/FIREWidget";
import { useWidgets } from "@/context/WidgetContext";

const Dashboard = () => {
  const { widgets } = useWidgets();

  return (
    <Layout>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground mb-1">Financial Dashboard</h1>
        <p className="text-muted-foreground">
          Visualize, track, and optimize your financial health in real time
        </p>
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 overflow-visible">
        {/* Top row */}
        {widgets.netWorth && (
          <div className="h-full">
            <NetWorthWidget />
          </div>
        )}

        {widgets.recentTransactions && (
          <div className="h-full">
            <TransactionsWidget />
          </div>
        )}

        {widgets.monthlyBudget && (
          <div className="h-full">
            <BudgetWidget />
          </div>
        )}

        {/* Middle row */}
        {widgets.savingsGoals && (
          <div className="h-full">
            <SavingsGoalsWidget />
          </div>
        )}

        {widgets.fireNumber && (
          <div className="h-full">
            <FIREWidget />
          </div>
        )}

        {/* Empty filler to align grid if needed */}
        <div className="hidden lg:block"></div>

        {/* Full-width bottom section */}
        {widgets.aiInsights && (
          <div className="lg:col-span-3">
            <AIInsightsWidget />
          </div>
        )}
      </div>
    </Layout>
  );
};

export default Dashboard;
