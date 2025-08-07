// Backtest functionality
async function runBacktest() {
    try {
        const symbol = document.getElementById('symbolSelect').value;
        const days = document.getElementById('backtestDays').value;
        
        // Show progress
        document.getElementById('backtestProgress').style.display = 'block';
        document.getElementById('progressFill').style.width = '0%';
        document.getElementById('progressText').textContent = 'Starting backtest...';
        
        // Simulate progress
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += Math.random() * 20;
            if (progress > 90) progress = 90;
            document.getElementById('progressFill').style.width = progress + '%';
            document.getElementById('progressText').textContent = `Running backtest... ${Math.round(progress)}%`;
        }, 500);
        
        const response = await fetch(`/api/backtest/run?symbol=${symbol}&days=${days}`, {
            method: 'POST'
        });
        const data = await response.json();
        
        clearInterval(progressInterval);
        document.getElementById('progressFill').style.width = '100%';
        document.getElementById('progressText').textContent = 'Backtest completed!';
        
        setTimeout(() => {
            document.getElementById('backtestProgress').style.display = 'none';
        }, 2000);
        
        if (data.error) {
            showAlert(data.error, 'error');
        } else {
            displayBacktestResults(data);
            showAlert('Backtest completed successfully!', 'success');
        }
        
    } catch (error) {
        document.getElementById('backtestProgress').style.display = 'none';
        showAlert('Error running backtest', 'error');
    }
}
function displayBacktestResults(results) {
    const container = document.getElementById('backtestResults');
    let html = '<div class="performance-grid">';
    let tradesHtml = '';

    for (const [symbol, result] of Object.entries(results)) {
        if (result.error) {
            html += `
                <div class="metric-card error">
                    <div class="metric-value">${symbol}</div>
                    <div class="metric-label">${result.error}</div>
                </div>
            `;
            continue;
        }

        // Calculate win rate safely
        const winRate = result.win_rate !== undefined 
            ? Math.round(result.win_rate) 
            : Math.round((result.winning_trades / (result.total_trades || 1)) * 100);

        const winRateColor = winRate >= 50 ? 'positive' : 'negative';
        const pnlColor = result.total_pnl >= 0 ? 'positive' : 'negative';

        // Add summary card
        html += `
            <div class="metric-card">
                <div class="metric-value">${symbol}</div>
                <div class="metric-label">
                    Trades: ${result.total_trades}<br>
                    Win Rate: <span class="${winRateColor}">${winRate}%</span><br>
                    P&L: <span class="${pnlColor}">₹${result.total_pnl?.toFixed(2) || 0}</span>
                </div>
            </div>
        `;

        // Populate Trade History tab
        if (result.trades && result.trades.length > 0) {
            const seenDates = new Set();

if (result.trades && result.trades.length > 0) {
    const seenDates = new Set();

    // Optional: sort by entry time DESCENDING to get latest trade per day
    const sortedTrades = [...result.trades].sort((a, b) => new Date(b.entry_time) - new Date(a.entry_time));

    sortedTrades.forEach(trade => {
        const tradeDate = new Date(trade.entry_time).toISOString().split("T")[0];

        if (seenDates.has(tradeDate)) return; // already added a trade for this date

        seenDates.add(tradeDate); // mark this date as handled

        const pnlClass = trade.pnl >= 0 ? 'positive' : 'negative';
        tradesHtml += `
            <tr>
                <td>${trade.symbol}</td>
                <td>${trade.signal}</td>
                <td>₹${trade.entry_price.toFixed(2)}</td>
                <td>₹${trade.exit_price.toFixed(2)}</td>
                <td class="${pnlClass}">₹${trade.pnl.toFixed(2)}</td>
                <td>${trade.exit_reason || ''}</td>
                <td>${new Date(trade.entry_time).toLocaleString()}</td>
                <td>${new Date(trade.exit_time).toLocaleString()}</td>
            </tr>
        `;
    });
};
        }
    }

    html += '</div>';
    container.innerHTML = html;

    // Update Trade History tab with latest trades
    document.getElementById('tradesBody').innerHTML = tradesHtml || `
        <tr><td colspan="6" style="text-align:center;">No trades executed</td></tr>
    `;
}



// Strategy performance
async function loadStrategyPerformance() {
    try {
        const response = await fetch('/api/strategy/performance');
        const data = await response.json();
        
        if (data.error) {
            document.getElementById('strategyPerformance').innerHTML = 
                `<div class="alert error">${data.error}</div>`;
            return;
        }
        
        const performanceHtml = `
            <div class="performance-grid">
                <div class="metric-card">
                    <div class="metric-value">${data.overall_trades}</div>
                    <div class="metric-label">Total Trades</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${data.overall_wins}</div>
                    <div class="metric-label">Winning Trades</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value ${data.overall_win_rate >= 50 ? 'positive' : 'negative'}">
                        ${data.overall_win_rate}%
                    </div>
                    <div class="metric-label">Win Rate</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value ${data.overall_pnl >= 0 ? 'positive' : 'negative'}">
                        ₹${data.overall_pnl}
                    </div>
                    <div class="metric-label">Total P&L</div>
                </div>
            </div>
        `;
        
        document.getElementById('strategyPerformance').innerHTML = performanceHtml;
        
        // Update trades table
        if (data.recent_trades && data.recent_trades.length > 0) {
            let tradesHtml = '';
            data.recent_trades.forEach(trade => {
                const pnlClass = trade.pnl >= 0 ? 'positive' : 'negative';
                tradesHtml += `
                    <tr>
                        <td>${trade.symbol}</td>
                        <td>${trade.signal}</td>
                        <td>₹${trade.entry_price}</td>
                        <td>₹${trade.exit_price}</td>
                        <td class="${pnlClass}">₹${trade.pnl}</td>
                        <td>${trade.exit_reason}</td>
                    </tr>
                `;
            });
            document.getElementById('tradesBody').innerHTML = tradesHtml;
        }
        
    } catch (error) {
        document.getElementById('strategyPerformance').innerHTML = 
            `<div class="alert error">Error loading performance: ${error.message}</div>`;
    }
}

// Utility functions
function showTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.nav-tab').forEach(tab => tab.classList.remove('active'));
    
    document.getElementById(tabName).classList.add('active');
    event.target.classList.add('active');
}

function showAlert(message, type = 'success') {
    const alertContainer = document.getElementById('alertContainer');
    const alert = document.createElement('div');
    alert.className = `alert ${type}`;
    alert.textContent = message;
    
    alertContainer.appendChild(alert);
    
    setTimeout(() => {
        alert.remove();
    }, 5000);
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    loadStrategyPerformance();
});