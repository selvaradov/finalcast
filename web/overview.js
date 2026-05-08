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
        labels: { color: CHALK, font: { family: "'Caveat', cursive", size: 15, weight: 700 }, padding: 16 }
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
    buildPopularityArrowChart(DATA);
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
            beginAtZero: true
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
            beginAtZero: true
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
            max: 70
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

    const SUBJECT_COLORS = {
      'Philosophy': BLUE,
      'Politics': RED,
      'Economics': GOLD
    };

    const SUBJECT_ORDER = {'Philosophy': 0, 'Politics': 1, 'Economics': 2};
    const sigPapers = Object.entries(catalogue)
      .filter(([, p]) => p.trend_p !== undefined && p.trend_p < 0.05)
      .sort((a, b) => (SUBJECT_ORDER[a[1].subject] ?? 9) - (SUBJECT_ORDER[b[1].subject] ?? 9)
        || a[0].localeCompare(b[0]));

    const years = ['2015','2016','2017','2018','2019','2020','2021','2022','2023','2024','2025'];

    const DASH_PATTERNS = [[], [5,5], [2,3]];
    const subjectIndex = {};

    const datasets = sigPapers.map(([name, p]) => {
      const ts = meansTs[name] || {};
      const color = SUBJECT_COLORS[p.subject] || CHALK;
      const idx = subjectIndex[p.subject] || 0;
      subjectIndex[p.subject] = idx + 1;
      const dir = p.trend_slope > 0 ? '+' : '';
      return {
        label: `${name} (${dir}${p.trend_slope.toFixed(2)}/yr)`,
        data: years.map(y => y === '2023' ? null : (ts[y] ?? null)),
        borderColor: color,
        backgroundColor: 'transparent',
        borderDash: DASH_PATTERNS[idx % DASH_PATTERNS.length],
        tension: 0,
        pointRadius: 3,
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
          legend: {
            ...CHART_DEFAULTS.plugins.legend,
            labels: {
              ...CHART_DEFAULTS.plugins.legend.labels,
              boxWidth: 28,
              boxHeight: 0
            }
          },
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

  function buildPopularityArrowChart(DATA) {
    const canvas = document.getElementById('popularity-arrow-chart');
    if (!canvas) return;

    const popularity = DATA.paper_popularity || {};
    const catalogue = DATA.paper_catalogue || {};

    const yearTotals = {};
    for (const yearData of Object.values(popularity)) {
      for (const [y, n] of Object.entries(yearData)) {
        yearTotals[y] = (yearTotals[y] || 0) + n;
      }
    }

    const currentPapers = Object.entries(popularity)
      .filter(([, yd]) => yd['2024'] !== undefined || yd['2025'] !== undefined);

    const items = currentPapers
      .map(([name, yearData]) => {
        const subject = catalogue[name]?.subject;
        if (!subject) return null;

        const pts = Object.entries(yearData)
          .filter(([y]) => yearTotals[y] && y !== '2023')
          .map(([y, n]) => [+y, (n / yearTotals[y]) * 100])
          .sort((a, b) => a[0] - b[0]);
        if (pts.length < 5) return null;

        // Early vs recent averages (actual values for display)
        const earlyPts = pts.slice(0, 3);
        const recentPts = pts.slice(-3);
        const startShare = earlyPts.reduce((s, p) => s + p[1], 0) / earlyPts.length;
        const endShare = recentPts.reduce((s, p) => s + p[1], 0) / recentPts.length;

        // OLS for significance filter only
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
        const t = se > 0 ? Math.abs(slope / se) : 0;
        const pApprox = Math.exp(-0.717 * t - 0.416 * t * t);
        const totalChange = slope * (pts[pts.length - 1][0] - pts[0][0]);

        if (pApprox >= 0.05 || Math.abs(totalChange) <= 1) return null;

        return { name, subject, startShare, endShare, change: endShare - startShare, slope, pApprox };
      })
      .filter(Boolean);

    // Sort by end share descending (biggest papers at top)
    items.sort((a, b) => b.endShare - a.endShare);

    const mobile = window.innerWidth <= 600;

    function wrapLabel(name) {
      if (!mobile || name.length <= 16) return name;
      const mid = Math.ceil(name.length / 2);
      let splitAt = name.lastIndexOf(' ', mid);
      if (splitAt <= 0) splitAt = name.indexOf(' ', mid);
      if (splitAt <= 0) return name;
      return [name.slice(0, splitAt), name.slice(splitAt + 1)];
    }

    const labels = items.map(d => wrapLabel(d.name));
    const xMax = Math.ceil(Math.max(...items.map(d => Math.max(d.startShare, d.endShare))) + 0.5);

    // Use scatter with points at midpoint of each arrow for tooltip hit area
    const midpoints = items.map((d, i) => ({
      x: (d.startShare + d.endShare) / 2,
      y: i
    }));

    new Chart(canvas, {
      type: 'scatter',
      data: {
        datasets: [{
          data: midpoints,
          pointRadius: items.map(d => Math.max(12, Math.abs(d.endShare - d.startShare) * 8)),
          pointHoverRadius: items.map(d => Math.max(14, Math.abs(d.endShare - d.startShare) * 8 + 2)),
          backgroundColor: 'transparent',
          borderWidth: 0
        }]
      },
      options: {
        ...CHART_DEFAULTS,
        plugins: {
          ...CHART_DEFAULTS.plugins,
          legend: { display: false },
          tooltip: {
            ...CHART_DEFAULTS.plugins.tooltip,
            mode: 'nearest',
            intersect: false,
            callbacks: {
              title: (ctx) => items[ctx[0]?.dataIndex]?.name || '',
              label: (item) => {
                const d = items[item.dataIndex];
                return [
                  `${d.startShare.toFixed(1)}% → ${d.endShare.toFixed(1)}%`,
                  `${d.slope > 0 ? '+' : ''}${d.slope.toFixed(2)} pp/yr`,
                  `p = ${d.pApprox < 0.001 ? '<0.001' : d.pApprox.toFixed(3)}`
                ];
              }
            }
          }
        },
        scales: {
          x: {
            ...CHART_DEFAULTS.scales.x,
            title: { display: true, text: 'Share of all sittings (%)', color: CHALK_DIM, font: { size: 12 } },
            min: 0,
            max: xMax
          },
          y: {
            ...CHART_DEFAULTS.scales.y,
            reverse: true,
            min: -0.5,
            max: items.length - 0.5,
            afterBuildTicks: (axis) => {
              axis.ticks = items.map((_, i) => ({ value: i }));
            },
            ticks: {
              color: CHALK_DIM,
              font: { size: mobile ? 10 : 11 },
              autoSkip: false,
              callback: (val) => Number.isInteger(val) ? (labels[val] || '') : ''
            },
            grid: { display: false }
          }
        }
      },
      plugins: [{
        id: 'arrows',
        afterDatasetsDraw(chart) {
          const ctx = chart.ctx;
          const xScale = chart.scales.x;
          const yScale = chart.scales.y;

          items.forEach((d, i) => {
            const x1 = xScale.getPixelForValue(d.startShare);
            const x2 = xScale.getPixelForValue(d.endShare);
            const cy = yScale.getPixelForValue(i);
            const color = d.change >= 0 ? BLUE : RED;
            const headLen = 10;
            const dir = x2 > x1 ? 1 : -1;

            ctx.save();
            // Shaft
            ctx.strokeStyle = color;
            ctx.lineWidth = 4;
            ctx.lineCap = 'round';
            ctx.beginPath();
            ctx.moveTo(x1, cy);
            ctx.lineTo(x2 - dir * headLen, cy);
            ctx.stroke();

            // Start dot
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(x1, cy, 5, 0, Math.PI * 2);
            ctx.fill();

            // Arrowhead
            ctx.beginPath();
            ctx.moveTo(x2, cy);
            ctx.lineTo(x2 - dir * headLen, cy - 7);
            ctx.lineTo(x2 - dir * headLen, cy + 7);
            ctx.closePath();
            ctx.fill();

            ctx.restore();
          });
        }
      }]
    });
  }

  function wireToc() {
    wireTocNav('.overview-toc');
  }


  function wireTocNav(selector) {
    const tocEl = document.querySelector(selector);
    if (!tocEl) return;
    const links = tocEl.querySelectorAll('a[data-scroll]');
    if (links.length === 0) return;

    const navH = 53;
    links.forEach(a => {
      a.addEventListener('click', (e) => {
        e.preventDefault();
        const target = document.getElementById(a.dataset.scroll);
        if (!target) return;
        const tocH = tocEl.offsetHeight || 0;
        const y = target.getBoundingClientRect().top + window.scrollY - navH - tocH - 12;
        window.scrollTo({ top: y, behavior: 'smooth' });
      });
    });

    const sections = Array.from(links).map(a => document.getElementById(a.dataset.scroll)).filter(Boolean);

    function update() {
      const mid = window.innerHeight / 2;
      let active = null;
      for (const s of sections) {
        if (s.getBoundingClientRect().top <= mid) {
          active = s.id;
        } else {
          break;
        }
      }
      links.forEach(a => a.classList.toggle('active', a.dataset.scroll === active));
    }

    window.addEventListener('scroll', update, { passive: true });
    update();
  }


  return { init, wireTocNav };
})();
