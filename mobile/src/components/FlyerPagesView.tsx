import React, { useCallback, useMemo, useState } from 'react';
import {
  FlatList,
  Image,
  NativeScrollEvent,
  NativeSyntheticEvent,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';

import { colors, font, radius, space } from '../theme';

/** How many of a brochure's pages we show. The backend stores every page it captured and
 *  serves them in reading order, so raising this is a one-line, OTA-only change — the
 *  first pages are where the chains put their best deals, which is why it starts small. */
export const FLYER_PAGE_CAP = 5;

type Props = {
  /** The chain's display name, e.g. "Lidl". */
  label: string;
  /** Every captured page, already ordered (biggest brochure first, then printed order). */
  pages: string[];
  onBack: () => void;
};

/**
 * The flyer as printed — a horizontal pager of page scans.
 *
 * Rendered as a VIEW inside StoresModal, never as its own `<Modal>`: two sibling modals
 * share a view controller and iOS refuses the second one, latching it dead for the whole
 * session. The "Change branch" picker in the same sheet is built the same way.
 */
export function FlyerPagesView({ label, pages, onBack }: Props) {
  const { width, height } = useWindowDimensions();
  const [index, setIndex] = useState(0);
  const shown = useMemo(() => pages.slice(0, FLYER_PAGE_CAP), [pages]);

  // The sheet's own 1px borders, so a page never bleeds under them.
  const pageW = Math.max(1, Math.round(width) - 2);
  // Flyer pages are portrait (~3:4). Cap against the viewport so the pager still fits
  // inside the sheet on a short screen rather than pushing the bar off.
  const pageH = Math.min(Math.round(pageW * 1.33), Math.round(height * 0.6));

  // Driven by `onScroll`, NOT `onMomentumScrollEnd`: react-native-web passes that prop
  // straight through to a handler nothing ever calls (the DOM has no momentum-end event),
  // so on web the counter would sit frozen at "1 / N" forever while the pages turned.
  // Measured in the browser, not assumed. `onScroll` fires on both platforms; the state
  // write is guarded on a real change so a 16 ms throttle costs no extra renders.
  const onScroll = useCallback(
    (e: NativeSyntheticEvent<NativeScrollEvent>) => {
      const raw = Math.round(e.nativeEvent.contentOffset.x / pageW);
      const next = Math.min(Math.max(raw, 0), Math.max(shown.length - 1, 0));
      setIndex((prev) => (prev === next ? prev : next));
    },
    [pageW, shown.length],
  );

  return (
    <View style={styles.wrap}>
      <View style={styles.bar}>
        <Pressable
          onPress={onBack}
          accessibilityRole="button"
          accessibilityLabel="Back to stores"
          hitSlop={8}
        >
          <Text style={styles.back}>‹ Back</Text>
        </Pressable>
        <Text style={styles.title} numberOfLines={1}>
          {label} flyer
        </Text>
        <Text style={styles.counter}>
          {shown.length ? `${index + 1} / ${shown.length}` : ''}
        </Text>
      </View>

      <FlatList
        testID="flyer-pager"
        data={shown}
        keyExtractor={(uri) => uri}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onScroll={onScroll}
        scrollEventThrottle={16}
        getItemLayout={(_d, i) => ({ length: pageW, offset: pageW * i, index: i })}
        renderItem={({ item }) => (
          // A per-page ScrollView is what gives iOS pinch-to-zoom on a dense flyer page
          // for free; on Android it is inert, and the page still reads at full width.
          <ScrollView
            style={{ width: pageW }}
            contentContainerStyle={styles.pageInner}
            maximumZoomScale={3}
            minimumZoomScale={1}
            showsHorizontalScrollIndicator={false}
            showsVerticalScrollIndicator={false}
          >
            <Image
              source={{ uri: item }}
              style={{ width: pageW, height: pageH }}
              resizeMode="contain"
              testID="flyer-page"
              accessible
              accessibilityRole="image"
              accessibilityLabel={`${label} flyer page`}
            />
          </ScrollView>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1 },
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.sm,
    paddingHorizontal: space.md,
    paddingBottom: space.sm,
  },
  back: { ...font.label, color: colors.accent },
  title: { ...font.body, color: colors.text, flex: 1 },
  counter: { ...font.small, color: colors.muted },
  pageInner: { alignItems: 'center', justifyContent: 'center', borderRadius: radius.sm },
});
