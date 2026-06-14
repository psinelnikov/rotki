<script setup lang="ts">
import { NoteLocation } from '@/modules/core/common/notes';
import SimpleStatistics from '@/modules/statistics/SimpleStatistics.vue';

definePage({
  meta: {
    noteLocation: NoteLocation.STATISTICS,
  },
  name: 'statistics-graphs',
});
</script>

<template>
  <SimpleStatistics />
</template>
