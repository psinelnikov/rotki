<script setup lang="ts">
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { LineChart, PieChart } from 'echarts/charts';
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
} from 'echarts/components';
import VChart from 'vue-echarts';
import { useStatisticsApi } from '@/modules/statistics/api/use-statistics-api';

use([
  CanvasRenderer,
  LineChart,
  PieChart,
  GridComponent,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
]);

const { t } = useI18n({ useScope: 'global' });
const api = useStatisticsApi();

const netValueData = ref<{ times: number[]; values: number[] }>({ times: [], values: [] });
const locationDistribution = ref<Array<{ name: string; value: number }>>([]);
const assetDistribution = ref<Array<{ name: string; value: number }>>([]);
const loading = ref<boolean>(true);

const netValueOption = computed(() => ({
  title: { text: t('statistics.net_value_over_time'), left: 'center' },
  tooltip: { trigger: 'axis' },
  xAxis: {
    type: 'time',
    data: netValueData.value.times.map(t => new Date(t * 1000).toLocaleDateString()),
  },
  yAxis: { type: 'value', name: 'USD' },
  series: [{
    data: netValueData.value.values,
    type: 'line',
    smooth: true,
    areaStyle: { opacity: 0.3 },
  }],
}));

const locationOption = computed(() => ({
  title: { text: t('statistics.by_location'), left: 'center' },
  tooltip: { trigger: 'item', formatter: '{b}: ${c} ({d}%)' },
  series: [{
    type: 'pie',
    radius: '50%',
    data: locationDistribution.value,
    emphasis: {
      itemStyle: {
        shadowBlur: 10,
        shadowOffsetX: 0,
        shadowColor: 'rgba(0, 0, 0, 0.5)',
      },
    },
  }],
}));

const assetOption = computed(() => ({
  title: { text: t('statistics.by_asset'), left: 'center' },
  tooltip: { trigger: 'item', formatter: '{b}: ${c} ({d}%)' },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    avoidLabelOverlap: false,
    itemStyle: {
      borderRadius: 10,
      borderColor: '#fff',
      borderWidth: 2,
    },
    data: assetDistribution.value,
  }],
}));

onMounted(async () => {
  try {
    loading.value = true;

    // Net value over time
    const netValue = await api.queryNetValueData(true);
    netValueData.value = {
      times: netValue.times,
      values: netValue.values,
    };

    // Location distribution
    const locations = await api.queryLatestLocationValueDistribution();
    locationDistribution.value = Object.entries(locations).map(([name, data]) => ({
      name,
      value: data.usdValue,
    }));

    // Asset distribution
    const assets = await api.queryLatestAssetValueDistribution();
    assetDistribution.value = assets.map(asset => ({
      name: asset.asset,
      value: asset.usdValue,
    })).slice(0, 10); // Top 10 assets
  }
  catch (error) {
    logger.error(error);
  }
  finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="container py-4">
    <div
      v-if="loading"
      class="flex items-center justify-center h-64"
    >
      <i class="text-2xl animate-spin ri-loader-4-line" />
    </div>
    <div
      v-else
      class="grid grid-cols-1 lg:grid-cols-2 gap-4"
    >
      <RuiCard class="lg:col-span-2">
        <VChart
          class="h-80 w-full"
          :option="netValueOption"
          autoresize
        />
      </RuiCard>
      <RuiCard>
        <VChart
          class="h-64 w-full"
          :option="locationOption"
          autoresize
        />
      </RuiCard>
      <RuiCard>
        <VChart
          class="h-64 w-full"
          :option="assetOption"
          autoresize
        />
      </RuiCard>
    </div>
  </div>
</template>
