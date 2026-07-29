// Every product sub-group is headed now, including one-offer ones, so the hardcoded
// plural "{count} offers" became reachable copy: it would render "1 offers".
//
// Assertions go through the `group-header-meta` testID, not a text query: the meta node's
// children are [count, ' offer(s)', <Text>], and RNTL only joins ADJACENT string children,
// so the nested "· from …" element breaks getByText on the whole line.
import { render, screen } from '@testing-library/react-native';
import React from 'react';

import { GroupHeader } from '../components/GroupHeader';

describe('GroupHeader', () => {
  it('says "1 offer" for a single-offer group', async () => {
    await render(<GroupHeader label="Kiwi" count={1} fromCents={249} />);
    // toHaveTextContent matches the WHOLE string here, so assert with regexes.
    expect(screen.getByTestId('group-header-meta')).toHaveTextContent(/\b1 offer\b/);
    expect(screen.getByTestId('group-header-meta')).not.toHaveTextContent(/1 offers/);
    // The price still shows — "from" on one offer is that offer's own price, which is
    // the whole point of heading it rather than hiding it in the bucket.
    expect(screen.getByTestId('group-header-meta')).toHaveTextContent(/2,49/);
  });

  it('says "N offers" for a comparison group', async () => {
    // Both directions are needed: the singular test alone passes an inverted ternary.
    await render(<GroupHeader label="Avocado" count={4} fromCents={88} />);
    expect(screen.getByTestId('group-header-meta')).toHaveTextContent(/\b4 offers\b/);
  });

  it('renders no meta at all for the muted "More" bucket', async () => {
    await render(<GroupHeader label="More" count={7} muted />);
    expect(screen.getByText('More')).toBeTruthy();
    expect(screen.queryByTestId('group-header-meta')).toBeNull();
  });
});
