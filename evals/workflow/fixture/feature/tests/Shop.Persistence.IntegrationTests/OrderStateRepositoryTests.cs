namespace Shop.Persistence.IntegrationTests;

public sealed class OrderStateRepositoryTests(DatabaseFixture fixture)
{
    [Fact]
    public async Task Set_MovesAPaidOrderToPacked_AndStoresTheNote()
    {
        await fixture.InsertOrderAsync("A-200", OrderState.Paid);

        var change = await fixture.Orders.SetStateAsync("A-200", OrderState.Packed, " boxed ", CancellationToken.None);

        var stored = await fixture.Orders.GetAsync("A-200", CancellationToken.None);
        Assert.Equal(OrderStateOutcome.Set, change.Outcome);
        Assert.Equal(OrderState.Paid, change.Previous);
        Assert.Equal(OrderState.Packed, stored!.State);
        Assert.Equal("boxed", stored.Note);
    }

    [Fact]
    public async Task Set_RefusesShipped_ForAPaidOrder()
    {
        await fixture.InsertOrderAsync("A-201", OrderState.Paid);

        var change = await fixture.Orders.SetStateAsync("A-201", OrderState.Shipped, "late", CancellationToken.None);

        var stored = await fixture.Orders.GetAsync("A-201", CancellationToken.None);
        Assert.Equal(OrderStateOutcome.NotAllowed, change.Outcome);
        Assert.Equal(OrderState.Paid, stored!.State);
        Assert.Equal(string.Empty, stored.Note);
    }
}
