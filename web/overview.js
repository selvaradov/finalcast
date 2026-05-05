const Overview = (() => {
  let initialized = false;

  const CHALK = '#e8e5dc';
  const CHALK_DIM = '#9a978e';
  const CHALK_FAINT = '#5e5c56';
  const BLUE = '#5b9bf5';
  const RED = '#e8614d';
  const GOLD = '#f0c75e';

  const CHART_DEFAULTS = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: { color: CHALK, font: { family: "'Caveat', cursive", size: 15, weight: 700 } }
      },
      tooltip: {
        backgroundColor: '#222228',
        titleColor: CHALK,
        bodyColor: CHALK_DIM,
        borderColor: 'rgba(232,229,220,0.12)',
        borderWidth: 1,
        titleFont: { family: "'Caveat', cursive", size: 15, weight: 700 },
        bodyFont: { family: "'Inter', system-ui", size: 12 },
        padding: 10
      }
    },
    scales: {
      x: {
        grid: { color: 'rgba(232,229,220,0.06)' },
        ticks: { color: CHALK_DIM, font: { size: 11 } }
      },
      y: {
        grid: { color: 'rgba(232,229,220,0.06)' },
        ticks: { color: CHALK_DIM, font: { size: 11 } }
      }
    }
  };

  function init(DATA) {
    if (initialized) return;
    initialized = true;

    buildFirstsChart(DATA);
    buildGenderChart(DATA);
    buildSubjectChart(DATA);
    buildClassDistChart(DATA);
    buildTrendsChart(DATA);
    buildPopularityChart(DATA);
    fillKingmakers(DATA);
    wireToc();
  }

  function buildFirstsChart(DATA) {
    const years = Object.keys(DATA.first_rates_by_year).sort();
    const rates = years.map(y => DATA.first_rates_by_year[y]);

    const is2020 = years.map(y => y === '2020');

    new Chart(document.getElementById('firsts-chart'), {
      type: 'line',
      data: {
        labels: years,
        datasets: [{
          label: 'First-class rate (%)',
          data: rates,
          borderColor: BLUE,
          backgroundColor: BLUE + '22',
          fill: true,
          tension: 0.3,
          pointRadius: years.map(y => y === '2020' ? 8 : 4),
          pointBackgroundColor: years.map(y => y === '2020' ? RED : BLUE),
          pointBorderColor: years.map(y => y === '2020' ? RED : BLUE),
          borderWidth: 2
        }]
      },
      options: {
        ...CHART_DEFAULTS,
        plugins: {
          ...CHART_DEFAULTS.plugins,
          annotation: undefined,
          tooltip: {
            ...CHART_DEFAULTS.plugins.tooltip,
            callbacks: {
              afterLabel: (item) => item.label === '2020' ? 'COVID year — excluded from model' : ''
            }
          }
        },
        scales: {
          ...CHART_DEFAULTS.scales,
          y: {
            ...CHART_DEFAULTS.scales.y,
            title: { display: true, text: '% First', color: CHALK_DIM, font: { size: 12 } },
            min: 0,
            max: 45
          }
        }
      }
    });
  }

  function buildGenderChart(DATA) {
    const genderTs = DATA.gender_class_ts || {};
    const years = Object.keys(genderTs).sort().filter(y => {
      const d = genderTs[y];
      return d.M && d.M['1st'] !== undefined && d.F && d.F['1st'] !== undefined;
    });

    const maleFirsts = years.map(y => genderTs[y].M['1st']);
    const femaleFirsts = years.map(y => genderTs[y].F['1st']);

    new Chart(document.getElementById('gender-chart'), {
      type: 'line',
      data: {
        labels: years,
        datasets: [
          {
            label: 'Male First rate',
            data: maleFirsts,
            borderColor: BLUE,
            backgroundColor: BLUE + '22',
            tension: 0.3,
            pointRadius: 4,
            borderWidth: 2
          },
          {
            label: 'Female First rate',
            data: femaleFirsts,
            borderColor: RED,
            backgroundColor: RED + '22',
            tension: 0.3,
            pointRadius: 4,
            borderWidth: 2
          }
        ]
      },
      options: {
        ...CHART_DEFAULTS,
        scales: {
          ...CHART_DEFAULTS.scales,
          y: {
            ...CHART_DEFAULTS.scales.y,
            title: { display: true, text: '% First', color: CHALK_DIM, font: { size: 12 } },
            min: 0,
            max: 55
          }
        }
      }
    });
  }

  function buildSubjectChart(DATA) {
    const subjects = DATA.subject_summary;

    new Chart(document.getElementById('subject-chart'), {
      type: 'bar',
      data: {
        labels: ['Philosophy', 'Politics', 'Economics'],
        datasets: [
          {
            label: 'Weighted mean mark',
            data: [subjects.Philosophy.weighted_mean, subjects.Politics.weighted_mean, subjects.Economics.weighted_mean],
            backgroundColor: [BLUE + '88', RED + '88', GOLD + '88'],
            borderColor: [BLUE, RED, GOLD],
            borderWidth: 1
          }
        ]
      },
      options: {
        ...CHART_DEFAULTS,
        indexAxis: 'y',
        plugins: {
          ...CHART_DEFAULTS.plugins,
          legend: { display: false },
          tooltip: {
            ...CHART_DEFAULTS.plugins.tooltip,
            callbacks: {
              afterLabel: (item) => {
                const subj = ['Philosophy', 'Politics', 'Economics'][item.dataIndex];
                const s = subjects[subj];
                return `SD: ${s.weighted_sd.toFixed(1)} · ${s.n_papers} papers · ${s.n_total} candidates`;
              }
            }
          }
        },
        scales: {
          x: {
            ...CHART_DEFAULTS.scales.x,
            title: { display: true, text: 'Weighted mean mark', color: CHALK_DIM, font: { size: 12 } },
            min: 60,
            max: 72
          },
          y: {
            ...CHART_DEFAULTS.scales.y,
            ticks: { color: CHALK, font: { family: "'Caveat', cursive", size: 16, weight: 700 } }
          }
        }
      }
    });
  }

  function buildClassDistChart(DATA) {
    const classTs = DATA.class_distribution_ts || {};
    const years = Object.keys(classTs).sort().filter(y => +y >= 2011);

    const classOrder = ['1st', '2.1', '2.2', '3rd'];
    const classColors = {
      '1st': BLUE,
      '2.1': CHALK,
      '2.2': GOLD,
      '3rd': CHALK_FAINT,
    };

    const datasets = classOrder.map(cls => ({
      label: cls,
      data: years.map(y => classTs[y]?.[cls] || 0),
      backgroundColor: classColors[cls] + '99',
      borderColor: classColors[cls],
      borderWidth: 1
    }));

    new Chart(document.getElementById('class-dist-chart'), {
      type: 'bar',
      data: { labels: years, datasets },
      options: {
        ...CHART_DEFAULTS,
        scales: {
          ...CHART_DEFAULTS.scales,
          x: { ...CHART_DEFAULTS.scales.x, stacked: true },
          y: {
            ...CHART_DEFAULTS.scales.y,
            stacked: true,
            title: { display: true, text: '% of cohort', color: CHALK_DIM, font: { size: 12 } },
            max: 100
          }
        }
      }
    });
  }

  function buildTrendsChart(DATA) {
    const canvas = document.getElementById('trends-chart');
    if (!canvas) return;

    const catalogue = DATA.paper_catalogue;
    const meansTs = DATA.paper_means_ts || {};

    const PAPER_COLORS = {
      'Philosophical Logic': BLUE,
      'Thesis in Politics': RED,
      'Microeconomic Analysis': GOLD
    };

    const sigPapers = Object.entries(catalogue)
      .filter(([, p]) => p.trend_p !== undefined && p.trend_p < 0.05)
      .sort((a, b) => a[0].localeCompare(b[0]));

    const years = ['2015','2016','2017','2018','2019','2020','2021','2022','2023','2024','2025'];

    const datasets = sigPapers.map(([name, p]) => {
      const ts = meansTs[name] || {};
      const color = PAPER_COLORS[name] || CHALK;
      const dir = p.trend_slope > 0 ? '+' : '';
      return {
        label: `${name} (${dir}${p.trend_slope.toFixed(2)}/yr)`,
        data: years.map(y => y === '2023' ? null : (ts[y] ?? null)),
        borderColor: color,
        backgroundColor: color + '22',
        tension: 0,
        pointRadius: 4,
        pointBackgroundColor: years.map(y => y === '2020' ? color + '55' : color),
        borderWidth: 2,
        spanGaps: true
      };
    });

    new Chart(canvas, {
      type: 'line',
      data: { labels: years, datasets },
      options: {
        ...CHART_DEFAULTS,
        plugins: {
          ...CHART_DEFAULTS.plugins,
          tooltip: {
            ...CHART_DEFAULTS.plugins.tooltip,
            callbacks: {
              afterLabel: (item) => {
                if (item.label === '2020') return 'COVID — marking normal, classification anomalous';
                if (item.label === '2023') return 'Boycott — no data';
                return '';
              }
            }
          }
        },
        scales: {
          ...CHART_DEFAULTS.scales,
          x: {
            ...CHART_DEFAULTS.scales.x,
            ticks: {
              color: (ctx) => {
                const v = years[ctx.index];
                return v === '2023' ? CHALK_FAINT : CHALK_DIM;
              },
              font: { size: 11 }
            }
          },
          y: {
            ...CHART_DEFAULTS.scales.y,
            title: { display: true, text: 'Fitted mean mark', color: CHALK_DIM, font: { size: 12 } }
          }
        }
      }
    });
  }

  function buildPopularityChart(DATA) {
    const canvas = document.getElementById('popularity-trends-chart');
    if (!canvas) return;

    const popularity = DATA.paper_popularity || {};
    const catalogue = DATA.paper_catalogue || {};

    // Compute total paper-sittings per year for share calculation
    const yearTotals = {};
    for (const yearData of Object.values(popularity)) {
      for (const [y, n] of Object.entries(yearData)) {
        yearTotals[y] = (yearTotals[y] || 0) + n;
      }
    }

    // Only include papers still available (have 2024 or 2025 data)
    const currentPapers = Object.entries(popularity)
      .filter(([, yd]) => yd['2024'] !== undefined || yd['2025'] !== undefined);

    const items = currentPapers
      .map(([name, yearData]) => {
        const subject = catalogue[name]?.subject;
        if (!subject) return null;

        // Convert to share of all paper-sittings (percentage points)
        const pts = Object.entries(yearData)
          .filter(([y]) => yearTotals[y] && y !== '2023')
          .map(([y, n]) => [+y, (n / yearTotals[y]) * 100])
          .sort((a, b) => a[0] - b[0]);
        if (pts.length < 5) return null;

        const n = pts.length;
        const meanX = pts.reduce((s, p) => s + p[0], 0) / n;
        const meanY = pts.reduce((s, p) => s + p[1], 0) / n;
        let ssxx = 0, ssxy = 0, ssyy = 0;
        for (const [x, y] of pts) {
          ssxx += (x - meanX) ** 2;
          ssxy += (x - meanX) * (y - meanY);
          ssyy += (y - meanY) ** 2;
        }
        const slope = ssxy / ssxx;
        const se = Math.sqrt(Math.max(0, (ssyy - slope * ssxy)) / ((n - 2) * ssxx));

        // Two-sided t-test p-value (approximation)
        const t = se > 0 ? Math.abs(slope / se) : 0;
        const df = n - 2;
        const pApprox = Math.exp(-0.717 * t - 0.416 * t * t);

        // Total change over the period (pp)
        const totalChange = slope * (pts[pts.length - 1][0] - pts[0][0]);

        return { name, subject, slope, totalChange, pApprox, avgShare: meanY, n };
      })
      .filter(Boolean)
      // Significant at 5% AND >1pp total change
      .filter(d => d.pApprox < 0.05 && Math.abs(d.totalChange) > 1);

    items.sort((a, b) => b.totalChange - a.totalChange);

    new Chart(canvas, {
      type: 'bar',
      data: {
        labels: items.map(d => d.name.length > 28 ? d.name.slice(0, 26) + '…' : d.name),
        datasets: [{
          label: 'Change in share (pp)',
          data: items.map(d => +d.totalChange.toFixed(1)),
          backgroundColor: items.map(d => (d.totalChange >= 0 ? BLUE : RED) + '88'),
          borderColor: items.map(d => d.totalChange >= 0 ? BLUE : RED),
          borderWidth: 1
        }]
      },
      options: {
        ...CHART_DEFAULTS,
        indexAxis: 'y',
        plugins: {
          ...CHART_DEFAULTS.plugins,
          legend: { display: false },
          tooltip: {
            ...CHART_DEFAULTS.plugins.tooltip,
            callbacks: {
              afterLabel: (item) => {
                const d = items[item.dataIndex];
                return `Avg share: ${d.avgShare.toFixed(1)}% · ${d.slope > 0 ? '+' : ''}${d.slope.toFixed(2)} pp/yr · p=${d.pApprox < 0.001 ? '<0.001' : d.pApprox.toFixed(3)}`;
              }
            }
          }
        },
        scales: {
          x: {
            ...CHART_DEFAULTS.scales.x,
            title: { display: true, text: 'Change in share of sittings (pp)', color: CHALK_DIM, font: { size: 12 } }
          },
          y: {
            ...CHART_DEFAULTS.scales.y,
            ticks: { color: CHALK_DIM, font: { size: 11 }, autoSkip: false }
          }
        }
      }
    });
  }

  function wireToc() {
    document.querySelectorAll('.overview-toc a[data-scroll]').forEach(a => {
      a.style.cursor = 'pointer';
      a.addEventListener('click', (e) => {
        e.preventDefault();
        const target = document.getElementById(a.dataset.scroll);
        if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });
  }

  function fillKingmakers(DATA) {
    const el = document.getElementById('kingmaker-list');
    if (!el || !DATA.kingmaker_papers) return;
    el.innerHTML = DATA.kingmaker_papers.map(p => {
      const color = p.subject === 'Economics' ? GOLD : p.subject === 'Politics' ? RED : BLUE;
      return `<span class="kingmaker-item"><span style="color:${color}">●</span> ${p.paper} <span class="kingmaker-sigma">σ=${p.sigma.toFixed(1)}</span></span>`;
    }).join('');
  }

  return { init };
})();
