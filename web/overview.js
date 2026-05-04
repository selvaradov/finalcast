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
    fillKingmakers(DATA);
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

  function fillKingmakers(DATA) {
    const el = document.getElementById('kingmaker-list');
    if (!el || !DATA.kingmaker_papers) return;
    el.textContent = DATA.kingmaker_papers.map(p => `${p.paper} (σ=${p.sigma.toFixed(1)})`).join(', ');
  }

  return { init };
})();
