export default () => (
  <board width="80mm" height="80mm" routingDisabled>
    {/* A: group has pcbX/pcbY, child has none */}
    <group name="A" pcbX={-25} pcbY={25}>
      <resistor name="RA" resistance="1k" footprint="0402" />
    </group>
    {/* B: group has pcbX/pcbY, child ALSO has local coords */}
    <group name="B" pcbX={25} pcbY={25}>
      <resistor name="RB" resistance="1k" footprint="0402" pcbX={5} pcbY={0} />
    </group>
    {/* C: plain group, child carries absolute coords */}
    <group name="C">
      <resistor name="RC" resistance="1k" footprint="0402" pcbX={-25} pcbY={-25} />
    </group>
    {/* D: no group at all */}
    <resistor name="RD" resistance="1k" footprint="0402" pcbX={25} pcbY={-25} />
  </board>
)
