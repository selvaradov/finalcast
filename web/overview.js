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
            min: 10,
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

    const sigPapers = Object.entries(catalogue)
      .filter(([, p]) => p.trend_p !== undefined && p.trend_p < 0.05)
      .sort((a, b) => a[1].trend_p - b[1].trend_p);

    const colors = [BLUE, RED, GOLD];
    const allYears = new Set();
    sigPapers.forEach(([name]) => {
      Object.keys(meansTs[name] || {}).forEach(y => allYears.add(y));
    });
    const years = [...allYears].sort().filter(y => y !== '2020');

    const datasets = sigPapers.map(([name, p], i) => {
      const ts = meansTs[name] || {};
      const color = colors[i % colors.length];
      const dir = p.trend_slope > 0 ? '+' : '';
      return {
        label: `${name} (${dir}${p.trend_slope.toFixed(2)}/yr)`,
        data: years.map(y => ts[y] ?? null),
        borderColor: color,
        backgroundColor: color + '22',
        tension: 0.3,
        pointRadius: 4,
        borderWidth: 2,
        spanGaps: true
      };
    });

    new Chart(canvas, {
      type: 'line',
      data: { labels: years, datasets },
      options: {
        ...CHART_DEFAULTS,
        scales: {
          ...CHART_DEFAULTS.scales,
          y: {
            ...CHART_DEFAULTS.scales.y,
            title: { display: true, text: 'Mean mark', color: CHALK_DIM, font: { size: 12 } }
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

    const changes = Object.entries(popularity)
      .map(([name, years]) => {
        const y2015 = years['2015'] || 0;
        const y2025 = years['2025'] || 0;
        if (y2015 < 20 || y2025 < 5) return null;
        return { name, y2015, y2025, change: y2025 - y2015, subject: catalogue[name]?.subject };
      })
      .filter(Boolean)
      .filter(d => d.subject);

    changes.sort((a, b) => b.change - a.change);
    const top = changes.slice(0, 8);
    const bottom = changes.slice(-8).reverse();
    const items = [...top, ...bottom];

    const subjectColor = (s) => s === 'Philosophy' ? BLUE : s === 'Politics' ? RED : GOLD;

    new Chart(canvas, {
      type: 'bar',
      data: {
        labels: items.map(d => d.name.length > 25 ? d.name.slice(0, 23) + '…' : d.name),
        datasets: [{
          label: 'Change in candidates (2015→2025)',
          data: items.map(d => d.change),
          backgroundColor: items.map(d => (d.change >= 0 ? BLUE : RED) + '88'),
          borderColor: items.map(d => d.change >= 0 ? BLUE : RED),
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
                return `${d.y2015} → ${d.y2025} candidates`;
              }
            }
          }
        },
        scales: {
          x: {
            ...CHART_DEFAULTS.scales.x,
            title: { display: true, text: 'Change in candidates', color: CHALK_DIM, font: { size: 12 } }
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
