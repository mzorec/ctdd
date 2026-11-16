namespace Shop.Application.IntegrationTests.Jobs;

public sealed class OrderJobsQueueTests(QueueFixture fixture)
{
    [Fact]
    public async Task Expand_WritesOneQueueRowPerRoute()
    {
        await fixture.SeedRoutesAsync(("fulfilment", "orders-out"), ("returns", "returns-out"));

        await fixture.Expansion.RunAsync(CancellationToken.None);

        Assert.Equal(2, await fixture.QueueRowsAsync());
    }
}
